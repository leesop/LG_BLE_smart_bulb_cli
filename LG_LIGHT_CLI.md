# LG Smart Lighting BLE CLI

Command-line test tool for reviving old LG Bluetooth smart bulbs whose official app is no longer practical to use.

This project was built from the original `LG 스마트 조명` Android APK (`com.lge.lightingble`, version `1.1.5`). The APK contains the BLE UUIDs and packet format used by LG smart bulbs such as `B1030EA5L6B`.

## Device Scope

Known target:

- `B1030EA5L6B`: LG Smart Bulb, warm/전구색 model

Likely compatible:

- `B1050EA5L6B`: same LG Smart Bulb family, daylight/주백색 model

The APK and LG release material mention `B1030EA5L6B` and `B1050EA5L6B` together, and the app protocol is not model-specific in the recovered control path. So `B1050EA5L6B` is expected to work if it exposes the same BLE service. Confirm with:

```sh
python3 lg_light_cli.py find-lg --timeout 15 --verify
```

## Project Files

- `lg_light_cli.py`: BLE CLI for scan, discovery, brightness, power, PIN, raw packets
- `LG_LIGHT_CLI.md`: this project overview and usage guide
- `ble_tools/`: local Python dependencies installed for this machine
- `.lg_light_cli.json`: created automatically to remember the last successfully controlled bulb address

## Protocol Summary

Recovered GATT values:

- Service UUID: `00001851-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000b1e7-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`
- Notify descriptor: `00002902-0000-1000-8000-00805f9b34fb`

Packet format:

```text
02 <cmd> <len> <payload...> ... 03
```

Packets are 19 bytes total.

Brightness/on/off uses `DIMMING`:

```text
cmd = 01
len = 08
payload = 00 00 <brightness> 00 00 00 01 00
```

On at 100:

```text
02 01 08 00 00 64 00 00 00 01 00 00 00 00 00 00 00 00 03
```

Off:

```text
02 01 08 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 03
```

## macOS Setup

The script uses `bleak`. In this workspace it is already installed into `ble_tools/`.

```sh
cd /Users/leesop/Documents/Codex/2026-05-09/lg
python3 lg_light_cli.py --help
```

macOS shows BLE devices as CoreBluetooth UUIDs, not printed MAC addresses. Use the address shown by this script.

## Raspberry Pi Setup

The code itself is portable: it uses Python and `bleak`, not macOS-specific Bluetooth APIs. On Raspberry Pi and ordinary x86 Linux, `bleak` talks to BlueZ.

Recommended setup on Raspberry Pi OS:

```sh
sudo apt update
sudo apt install -y python3 python3-pip bluetooth bluez
sudo systemctl enable --now bluetooth
python3 -m pip install -r requirements.txt
```

Recommended setup on Debian/Ubuntu x86 Linux is the same:

```sh
sudo apt update
sudo apt install -y python3 python3-pip bluetooth bluez
sudo systemctl enable --now bluetooth
python3 -m pip install -r requirements.txt
```

If you copy this whole folder from macOS to a Raspberry Pi or Linux PC, reinstall dependencies on that machine. A local `ble_tools/` folder installed on macOS should not be reused as-is on Linux.

One option:

```sh
rm -rf ble_tools
python3 -m pip install --target ble_tools bleak
```

If scanning or connecting fails on Linux, check:

```sh
bluetoothctl show
bluetoothctl power on
rfkill list bluetooth
```

Depending on the OS image and permissions, you may need to run the script with `sudo` or add your user to the appropriate Bluetooth-related group.

## Other Platforms

`bleak` also supports Windows through the WinRT BLE backend. This script has no OS-specific Bluetooth calls, so Windows should be possible with Python 3.10+ and a BLE-capable adapter. The recovered LG protocol is platform-independent; platform issues are usually permissions, Bluetooth stack, or adapter support.

Current `bleak` compatibility baseline:

- Linux with BlueZ 5.55+
- macOS 10.15+
- Windows 10 version 16299+
- Android is community-supported through Python-for-Android, but this CLI has not been shaped for mobile terminal workflows.

References:

- https://bleak.readthedocs.io/
- https://pypi.org/project/bleak/

## Find The Bulb

Use the LG-specific finder first:

```sh
python3 lg_light_cli.py find-lg --timeout 15
```

Verify candidates by connecting and checking the LG GATT service:

```sh
python3 lg_light_cli.py find-lg --timeout 15 --verify
```

Filtered scan:

```sh
python3 lg_light_cli.py scan --timeout 15 --lg-only
```

Full scan:

```sh
python3 lg_light_cli.py scan --timeout 15
```

Power-cycling the bulb immediately before scanning can make it easier to find.

## Inspect Services

```sh
python3 lg_light_cli.py services --address <ADDRESS>
```

After a successful control command, the address is remembered, so this can also be:

```sh
python3 lg_light_cli.py services
```

## Control

First command with explicit address:

```sh
python3 lg_light_cli.py monitor --address <ADDRESS>
python3 lg_light_cli.py on --address <ADDRESS>
python3 lg_light_cli.py brightness 50 --address <ADDRESS>
python3 lg_light_cli.py off --address <ADDRESS>
```

After any successful write, the address is remembered in `.lg_light_cli.json`. Later commands can omit `--address`:

```sh
python3 lg_light_cli.py on
python3 lg_light_cli.py brightness 35
python3 lg_light_cli.py off
```

Show or clear the remembered address:

```sh
python3 lg_light_cli.py remembered
python3 lg_light_cli.py forget
```

If writes fail, try write-with-response:

```sh
python3 lg_light_cli.py on --address <ADDRESS> --response
```

If the recovered LG characteristic UUIDs are not exposed but you want to probe the first writable characteristic:

```sh
python3 lg_light_cli.py on --address <ADDRESS> --response --auto-characteristics
```

Use `--auto-characteristics` only when you are confident the selected device is the bulb.

## PIN Commands

Request PIN state:

```sh
python3 lg_light_cli.py pin-req --address <ADDRESS>
```

Set a 4-digit PIN:

```sh
python3 lg_light_cli.py pin-set 1234 --address <ADDRESS>
```

The recovered APK encodes `PIN_CODE_SET` by taking a zero-padded 4-digit ASCII PIN and adding `0x55`, `0x66`, `0x77`, and `0x88` to each digit, then appending `01`.

## Dry Run

Dry run prints packet hex without using Bluetooth:

```sh
python3 lg_light_cli.py on --dry-run
python3 lg_light_cli.py off --dry-run
python3 lg_light_cli.py brightness 35 --dry-run
python3 lg_light_cli.py monitor --dry-run
python3 lg_light_cli.py pin-set 1234 --dry-run
```

## Raw Packet

```sh
python3 lg_light_cli.py raw "02 01 08 00 00 64 00 00 00 01 00 00 00 00 00 00 00 00 03" --address <ADDRESS>
```

## License

This project is distributed under the GNU General Public License v3.0 or later (`GPL-3.0-or-later`). See `LICENSE`.
