#!/usr/bin/env python3
# SPDX-License-Identifier: Unlicense
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path


LOCAL_DEPS = Path(__file__).resolve().parent / "ble_tools"
CONFIG_PATH = Path(__file__).resolve().parent / ".lg_light_cli.json"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))


SERVICE_UUID = "00001851-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000b1e7-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"
LG_NAME_HINTS = (
    "lighting",
    "smartlight",
    "smart light",
    "lglighting",
    "lg lighting",
    "lg smart",
)

CMD_DIMMING = 0x01
CMD_MONITORING = 0x02
CMD_PIN_CODE_SET = 0x0D
CMD_PIN_CODE_REQ = 0x0E
CMD_RESET = 0x0F
CMD_DISCONNECT = 0x0B


def load_bleak():
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError as exc:
        raise SystemExit(
            "bleak is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from exc
    return BleakClient, BleakScanner


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remember_address(address: str) -> None:
    config = load_config()
    config["last_address"] = address
    save_config(config)


def remembered_address() -> str | None:
    value = load_config().get("last_address")
    return value if isinstance(value, str) and value else None


def clear_remembered_address() -> None:
    config = load_config()
    config.pop("last_address", None)
    save_config(config)


def resolve_address(address: str | None) -> str:
    if address:
        return address
    saved = remembered_address()
    if saved:
        print(f"using remembered address: {saved}")
        return saved
    raise SystemExit("--address is required. Run find-lg/scan first, or control a bulb once with --address.")


def hex_bytes(data: bytes | bytearray) -> str:
    return " ".join(f"{byte:02x}" for byte in data)


def normalize_uuid(value: str | None) -> str | None:
    return value.lower() if value else None


def advertisement_services(adv) -> list[str]:
    if adv is None:
        return []
    service_uuids = getattr(adv, "service_uuids", None) or []
    return [uuid.lower() for uuid in service_uuids]


def device_services(device, adv=None) -> list[str]:
    services = advertisement_services(adv)
    if services:
        return services
    service_uuids = getattr(getattr(device, "details", None), "service_uuids", None)
    if not service_uuids and getattr(device, "metadata", None):
        service_uuids = device.metadata.get("uuids")
    return [uuid.lower() for uuid in service_uuids or []]


def device_name(device, adv=None) -> str:
    return (
        getattr(adv, "local_name", None)
        or getattr(device, "name", None)
        or ""
    )


def looks_like_lg_light(device, adv=None) -> bool:
    services = device_services(device, adv)
    if SERVICE_UUID.lower() in services:
        return True
    name = device_name(device, adv).lower().replace(":", "").replace("-", " ")
    return any(hint in name for hint in LG_NAME_HINTS)


def print_device(device, adv=None, prefix: str = "  ") -> None:
    details = []
    name = device_name(device, adv)
    if name:
        details.append(name)
    details.append(device.address)
    rssi = getattr(adv, "rssi", None)
    if rssi is not None:
        details.append(f"rssi={rssi}")
    services = device_services(device, adv)
    if services:
        details.append("services=" + ",".join(services))
    print(prefix + "  ".join(details))


def parse_hex(value: str) -> bytes:
    compact = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(compact) % 2:
        raise argparse.ArgumentTypeError("hex string must contain whole bytes")
    return bytes.fromhex(compact)


def make_packet(command: int, length: int, payload: bytes = b"") -> bytes:
    if len(payload) > 15:
        raise ValueError("payload is too long for the 19-byte LG packet")
    packet = bytearray(19)
    packet[0] = 0x02
    packet[1] = command & 0xFF
    packet[2] = length & 0xFF
    packet[3 : 3 + len(payload)] = payload
    packet[18] = 0x03
    return bytes(packet)


def brightness_packet(value: int) -> bytes:
    if not 0 <= value <= 100:
        raise ValueError("brightness must be 0..100")
    payload = bytes([0x00, 0x00, value, 0x00, 0x00, 0x00, 0x01, 0x00])
    return make_packet(CMD_DIMMING, 0x08, payload)


def monitoring_packet() -> bytes:
    return make_packet(CMD_MONITORING, 0x03, bytes([0x00, 0x01, 0x00]))


def pin_request_packet() -> bytes:
    return make_packet(CMD_PIN_CODE_REQ, 0x01, bytes([0x00]))


def pin_set_packet(pin: int) -> bytes:
    if not 0 <= pin <= 9999:
        raise ValueError("pin must be 0..9999")
    digits = f"{pin:04d}".encode("ascii")
    payload = bytes(
        [
            (digits[0] + 0x55) & 0xFF,
            (digits[1] + 0x66) & 0xFF,
            (digits[2] + 0x77) & 0xFF,
            (digits[3] + 0x88) & 0xFF,
            0x01,
        ]
    )
    return make_packet(CMD_PIN_CODE_SET, 0x06, payload)


def reset_packet() -> bytes:
    return make_packet(CMD_RESET, 0x03, bytes([0x00, 0x00, 0x00]))


def disconnect_packet() -> bytes:
    return make_packet(CMD_DISCONNECT, 0x00)


def command_packet(args: argparse.Namespace) -> bytes | None:
    if args.command == "on":
        return brightness_packet(args.value)
    if args.command == "off":
        return brightness_packet(0)
    if args.command == "brightness":
        return brightness_packet(args.value)
    if args.command == "monitor":
        return monitoring_packet()
    if args.command == "pin-req":
        return pin_request_packet()
    if args.command == "pin-set":
        return pin_set_packet(args.pin)
    if args.command == "reset":
        return reset_packet()
    if args.command == "disconnect":
        return disconnect_packet()
    if args.command == "raw":
        data = parse_hex(args.hex)
        if len(data) != 19:
            raise ValueError("raw packet must be exactly 19 bytes")
        return data
    return None


async def scan(timeout: float, lg_only: bool) -> None:
    _, BleakScanner = load_bleak()
    print(f"Scanning for {timeout:g}s...")
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    rows = list(found.values()) if isinstance(found, dict) else [(device, None) for device in found]
    if lg_only:
        rows = [(device, adv) for device, adv in rows if looks_like_lg_light(device, adv)]

    if not rows:
        print("  no matching devices found")
        return

    for device, adv in rows:
        print_device(device, adv)


async def verify_lg_device(address: str, timeout: float) -> bool:
    BleakClient, _ = load_bleak()
    try:
        async with BleakClient(address, timeout=timeout) as client:
            service_ids = {service.uuid.lower() for service in client.services}
            return SERVICE_UUID.lower() in service_ids
    except Exception as exc:
        print(f"  {address} verify failed: {exc}")
        return False


async def find_lg(timeout: float, verify: bool, connect_timeout: float) -> None:
    _, BleakScanner = load_bleak()
    print(f"Finding LG smart lights for {timeout:g}s...")
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    rows = list(found.values()) if isinstance(found, dict) else [(device, None) for device in found]
    candidates = [(device, adv) for device, adv in rows if looks_like_lg_light(device, adv)]

    if not candidates:
        print("  no advertisement-level candidates found")
        print("  Try power-cycling the bulb, then run this again.")
        return

    print("Candidates:")
    for device, adv in candidates:
        print_device(device, adv)

    if not verify:
        return

    print("Verifying GATT service...")
    verified = []
    for device, adv in candidates:
        if await verify_lg_device(device.address, connect_timeout):
            verified.append((device, adv))

    if not verified:
        print("  no candidates exposed the LG control service after connect")
        return

    print("Verified LG control candidates:")
    for device, adv in verified:
        print_device(device, adv)


async def print_services(address: str) -> None:
    BleakClient, _ = load_bleak()
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        print_gatt(client)


def print_gatt(client) -> None:
    for service in client.services:
        print(f"[service] {service.uuid} {service.description}")
        for char in service.characteristics:
            props = ",".join(char.properties)
            print(f"  [char] {char.uuid} {props} {char.description}")


def find_characteristic(client: BleakClient, uuid: str | None, prop: str):
    wanted = normalize_uuid(uuid)
    fallback = None
    for service in client.services:
        for char in service.characteristics:
            if wanted and normalize_uuid(char.uuid) == wanted:
                return char
            if fallback is None and prop in char.properties:
                fallback = char
    return fallback


async def write_packet(
    address: str,
    packet: bytes,
    response: bool,
    listen: float,
    write_uuid: str,
    notify_uuid: str | None,
    auto_characteristics: bool,
) -> None:
    BleakClient, _ = load_bleak()

    def on_notify(_: int, data: bytearray) -> None:
        print(f"notify {hex_bytes(data)}")

    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        notify_enabled = False
        notify_char = None
        if notify_uuid or auto_characteristics:
            notify_char = find_characteristic(client, notify_uuid, "notify")
        if notify_char is not None:
            try:
                await client.start_notify(notify_char, on_notify)
                notify_enabled = True
                print(f"notify {notify_char.uuid}")
            except Exception as exc:
                print(f"notify not enabled: {exc}")
        elif notify_uuid:
            print(f"notify characteristic not found: {notify_uuid}")

        write_char = find_characteristic(client, write_uuid, "write")
        if write_char is None:
            write_char = find_characteristic(client, write_uuid, "write-without-response")
        if write_char is None:
            print("write characteristic not found. Available GATT:")
            print_gatt(client)
            raise SystemExit(2)
        if normalize_uuid(write_char.uuid) != normalize_uuid(write_uuid):
            print(f"using fallback writable characteristic: {write_char.uuid}")
        print(f"write  {hex_bytes(packet)}")
        await client.write_gatt_char(write_char, packet, response=response)

        if listen > 0:
            await asyncio.sleep(listen)

        if notify_enabled:
            await client.stop_notify(notify_char)

    remember_address(address)
    print(f"remembered address: {address}")


async def main_async(args: argparse.Namespace) -> None:
    if args.command == "scan":
        await scan(args.timeout, args.lg_only)
        return

    if args.command == "find-lg":
        await find_lg(args.timeout, args.verify, args.connect_timeout)
        return

    if args.command == "services":
        await print_services(resolve_address(args.address))
        return

    if args.command == "remembered":
        saved = remembered_address()
        print(saved or "no remembered address")
        return

    if args.command == "forget":
        clear_remembered_address()
        print("forgot remembered address")
        return

    packet = command_packet(args)
    if packet is None:
        raise ValueError(f"unsupported command: {args.command}")

    if args.dry_run:
        print(hex_bytes(packet))
        return

    address = resolve_address(args.address)

    await write_packet(
        address,
        packet,
        args.response,
        args.listen,
        args.write_uuid,
        args.notify_uuid,
        args.auto_characteristics,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LG Smart Lighting BLE test CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="scan for nearby BLE devices")
    scan_parser.add_argument("--timeout", type=float, default=8.0)
    scan_parser.add_argument("--lg-only", action="store_true", help="show only likely LG smart lights")

    find_parser = subparsers.add_parser("find-lg", help="find likely LG smart lights")
    find_parser.add_argument("--timeout", type=float, default=12.0)
    find_parser.add_argument("--verify", action="store_true", help="connect to candidates and check LG GATT service")
    find_parser.add_argument("--connect-timeout", type=float, default=8.0)

    services_parser = subparsers.add_parser("services", help="print GATT services")
    services_parser.add_argument("--address")

    subparsers.add_parser("remembered", help="print the remembered bulb address")
    subparsers.add_parser("forget", help="clear the remembered bulb address")

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--address", help="BLE address/UUID shown by scan")
        subparser.add_argument("--dry-run", action="store_true", help="only print packet hex")
        subparser.add_argument("--response", action="store_true", help="write with response")
        subparser.add_argument("--listen", type=float, default=1.0, help="seconds to wait for notify")
        subparser.add_argument("--write-uuid", default=WRITE_UUID, help="override write characteristic UUID")
        subparser.add_argument("--notify-uuid", default=NOTIFY_UUID, help="override notify characteristic UUID")
        subparser.add_argument(
            "--auto-characteristics",
            action="store_true",
            help="fallback to the first writable/notify characteristic when LG UUIDs are missing",
        )

    on_parser = subparsers.add_parser("on", help="turn on with brightness")
    add_common(on_parser)
    on_parser.add_argument("--value", type=int, default=100)

    off_parser = subparsers.add_parser("off", help="turn off")
    add_common(off_parser)

    brightness_parser = subparsers.add_parser("brightness", help="set brightness 0..100")
    add_common(brightness_parser)
    brightness_parser.add_argument("value", type=int)

    for name in ["monitor", "pin-req", "reset", "disconnect"]:
        add_common(subparsers.add_parser(name))

    pin_parser = subparsers.add_parser("pin-set", help="set a 4-digit PIN")
    add_common(pin_parser)
    pin_parser.add_argument("pin", type=int)

    raw_parser = subparsers.add_parser("raw", help="write a 19-byte raw hex packet")
    add_common(raw_parser)
    raw_parser.add_argument("hex")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
