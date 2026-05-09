# LG Smart Lighting BLE CLI

Command-line tool for controlling old LG Bluetooth smart bulbs when the official mobile app is no longer usable.

This project is based on analysis of the official Android app `LG 스마트 조명` (`com.lge.lightingble`, version `1.1.5`). The recovered information includes the BLE service UUIDs, characteristic UUIDs, and the 19-byte control packet format used by the bulb.

Korean documentation is available in `README.md`. A more detailed protocol note is available in `LG_LIGHT_CLI.md`.

## Supported Devices

Confirmed target:

- `B1030EA5L6B`: LG Smart Bulb, warm-white model

Likely compatible:

- `B1050EA5L6B`: same LG Smart Bulb family, daylight-white model

The recovered control path does not appear to branch by model. `B1050EA5L6B` is expected to work if it exposes the same LG BLE service:

```text
00001851-0000-1000-8000-00805f9b34fb
```

## Quick Start

Install dependencies:

```sh
python3 -m pip install -r requirements.txt
```

Find the bulb:

```sh
python3 lg_light_cli.py find-lg --timeout 15 --verify
```

Control it:

```sh
python3 lg_light_cli.py on --address <ADDRESS>
python3 lg_light_cli.py brightness 50
python3 lg_light_cli.py off
```

After one successful control command, the address is saved to `.lg_light_cli.json`, so later commands can omit `--address`.

```sh
python3 lg_light_cli.py remembered
python3 lg_light_cli.py forget
```

## Commands

Find likely LG bulbs:

```sh
python3 lg_light_cli.py find-lg --timeout 15
python3 lg_light_cli.py find-lg --timeout 15 --verify
```

Scan with LG filtering:

```sh
python3 lg_light_cli.py scan --timeout 15 --lg-only
```

Inspect GATT services:

```sh
python3 lg_light_cli.py services --address <ADDRESS>
```

Control:

```sh
python3 lg_light_cli.py monitor --address <ADDRESS>
python3 lg_light_cli.py on --address <ADDRESS>
python3 lg_light_cli.py brightness 35 --address <ADDRESS>
python3 lg_light_cli.py off --address <ADDRESS>
```

Print packets without using Bluetooth:

```sh
python3 lg_light_cli.py on --dry-run
python3 lg_light_cli.py off --dry-run
python3 lg_light_cli.py brightness 35 --dry-run
```

## Compatibility

The CLI uses the Python `bleak` library, which provides BLE backends for common desktop and Linux environments.

- macOS: CoreBluetooth backend
- Linux x86/x86_64/aarch64: BlueZ D-Bus backend
- Raspberry Pi: Linux/BlueZ backend
- Windows: WinRT backend

Recommended baseline:

- Python 3.10 or newer
- Bluetooth Low Energy capable adapter
- Linux with BlueZ 5.55 or newer
- macOS 10.15 or newer
- Windows 10 version 16299 or newer

Debian/Ubuntu or Raspberry Pi OS setup:

```sh
sudo apt update
sudo apt install -y python3 python3-pip bluetooth bluez
sudo systemctl enable --now bluetooth
python3 -m pip install -r requirements.txt
```

If scanning or connecting fails on Linux, check:

```sh
bluetoothctl show
bluetoothctl power on
rfkill list bluetooth
```

Some Linux systems may require `sudo` or additional Bluetooth permissions for scanning and connecting.

## Protocol Summary

Recovered GATT values:

- Service UUID: `00001851-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000b1e7-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`
- Notify descriptor: `00002902-0000-1000-8000-00805f9b34fb`

Packets are fixed at 19 bytes:

```text
02 <cmd> <len> <payload...> ... 03
```

Brightness and power use the `DIMMING` command:

```text
02 01 08 00 00 <brightness> 00 00 00 01 00 00 00 00 00 00 00 00 03
```

On at brightness 100:

```text
02 01 08 00 00 64 00 00 00 01 00 00 00 00 00 00 00 00 03
```

Off:

```text
02 01 08 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 03
```

## Notes

This is an experimental recovery tool for discontinued or legacy hardware. Firmware update/OAD support is not implemented.

## License

This project is distributed under the `Unlicense`, which is close to a public-domain/freeware release. You may copy, modify, distribute, and use it commercially. See `LICENSE`.
