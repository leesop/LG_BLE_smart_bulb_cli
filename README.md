# LG 스마트 조명 BLE CLI

공식 앱을 쓰기 어려워진 구형 LG 블루투스 스마트 전구를 커맨드라인에서 다시 제어하기 위한 실험용 도구입니다.

이 프로젝트는 LG 공식 Android 앱 `LG 스마트 조명` APK(`com.lge.lightingble`, `1.1.5`)를 분석해 BLE 서비스 UUID, characteristic UUID, 19바이트 제어 패킷 구조를 복원한 결과를 바탕으로 합니다.

English documentation is available in `README.en.md`.

## 지원 대상

확인 대상:

- `B1030EA5L6B`: LG 스마트 전구 전구색 모델

호환 가능성이 높은 대상:

- `B1050EA5L6B`: 같은 LG 스마트 전구 라인의 주백색 모델

두 모델은 같은 공식 앱/제품군에서 함께 다뤄지고, 복원된 제어 경로는 모델별 분기가 없습니다. 따라서 `B1050EA5L6B`도 같은 BLE 서비스(`00001851-0000-1000-8000-00805f9b34fb`)를 노출한다면 동작할 가능성이 높습니다.

## 빠른 시작

```sh
python3 -m pip install -r requirements.txt
python3 lg_light_cli.py find-lg --timeout 15 --verify
```

전구 주소를 찾은 뒤:

```sh
python3 lg_light_cli.py on --address <ADDRESS>
python3 lg_light_cli.py brightness 50
python3 lg_light_cli.py off
```

한 번 성공적으로 제어한 주소는 `.lg_light_cli.json`에 저장되며, 다음 명령부터는 `--address`를 생략할 수 있습니다.

```sh
python3 lg_light_cli.py remembered
python3 lg_light_cli.py forget
```

## 주요 명령

LG 스마트 전구 후보 찾기:

```sh
python3 lg_light_cli.py find-lg --timeout 15
python3 lg_light_cli.py find-lg --timeout 15 --verify
```

서비스 목록 확인:

```sh
python3 lg_light_cli.py services --address <ADDRESS>
```

제어:

```sh
python3 lg_light_cli.py monitor --address <ADDRESS>
python3 lg_light_cli.py on --address <ADDRESS>
python3 lg_light_cli.py brightness 35 --address <ADDRESS>
python3 lg_light_cli.py off --address <ADDRESS>
```

패킷만 확인:

```sh
python3 lg_light_cli.py on --dry-run
python3 lg_light_cli.py off --dry-run
python3 lg_light_cli.py brightness 35 --dry-run
```

## 호환성

이 CLI는 Python의 `bleak` 라이브러리를 사용합니다. `bleak`은 운영체제별 BLE 백엔드를 추상화합니다.

- macOS: CoreBluetooth 백엔드
- Linux x86/x86_64/aarch64: BlueZ D-Bus 백엔드
- Raspberry Pi: Linux/BlueZ 백엔드
- Windows: WinRT 백엔드

권장 조건:

- Python 3.10 이상
- Bluetooth Low Energy 지원 어댑터
- Linux에서는 BlueZ 5.55 이상과 실행 권한
- macOS 10.15 이상
- Windows 10 version 16299 이상

일반 x86 Linux 설치 예:

```sh
sudo apt update
sudo apt install -y python3 python3-pip bluetooth bluez
sudo systemctl enable --now bluetooth
python3 -m pip install -r requirements.txt
```

Raspberry Pi OS에서도 동일하게 설치할 수 있습니다.

```sh
sudo apt update
sudo apt install -y python3 python3-pip bluetooth bluez
sudo systemctl enable --now bluetooth
python3 -m pip install -r requirements.txt
```

Linux에서 문제가 있으면 다음을 확인하세요.

```sh
bluetoothctl show
bluetoothctl power on
rfkill list bluetooth
```

일부 배포판에서는 BLE 스캔/연결 권한 때문에 `sudo`가 필요할 수 있습니다.

## 프로토콜 요약

복원된 GATT 값:

- Service UUID: `00001851-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000b1e7-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`
- Notify descriptor: `00002902-0000-1000-8000-00805f9b34fb`

패킷은 19바이트 고정입니다.

```text
02 <cmd> <len> <payload...> ... 03
```

켜기/밝기 조절:

```text
02 01 08 00 00 <brightness> 00 00 00 01 00 00 00 00 00 00 00 00 03
```

밝기 100:

```text
02 01 08 00 00 64 00 00 00 01 00 00 00 00 00 00 00 00 03
```

끄기:

```text
02 01 08 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 03
```

## 저장소에 포함하지 않는 것

APK, DEX 추출물, 로컬 설치 패키지, 실행 상태 파일은 `.gitignore`에 포함되어 있습니다. GitHub에는 소스, 문서, `requirements.txt`만 올리면 됩니다.

## 주의

이 프로젝트는 단종/구형 기기를 개인적으로 복구하기 위한 실험용 도구입니다. 펌웨어 업데이트(OAD) 기능은 구현하지 않았습니다.

## 라이선스

GNU General Public License v3.0 or later (`GPL-3.0-or-later`)로 배포합니다. 자세한 내용은 `LICENSE` 파일을 참고하세요.

## 참고

- `bleak` 공식 문서: https://bleak.readthedocs.io/
- `bleak` PyPI: https://pypi.org/project/bleak/
