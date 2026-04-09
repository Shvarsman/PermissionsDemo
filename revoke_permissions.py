#!/usr/bin/env python3
import subprocess
import argparse
import sys
import os
import shutil

DEFAULT_PACKAGE = "com.shvarsman.permissionsdemo"

PERMISSIONS = {
    "CAMERA":   "android.permission.CAMERA",
    "CONTACTS": "android.permission.READ_CONTACTS",
    "LOCATION": "android.permission.ACCESS_FINE_LOCATION",
}

# ---------------------------------------------------------------
# Поиск adb
# ---------------------------------------------------------------

def find_adb() -> str | None:
    # 1. Уже есть в PATH
    found = shutil.which("adb")
    if found:
        return found

    # 2. Стандартные места установки Android SDK на Windows
    candidates = []

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    android_home   = os.environ.get("ANDROID_HOME", "")
    android_sdk    = os.environ.get("ANDROID_SDK_ROOT", "")

    if local_app_data:
        candidates.append(os.path.join(local_app_data,
            "Android", "Sdk", "platform-tools", "adb.exe"))

    if android_home:
        candidates.append(os.path.join(android_home,
            "platform-tools", "adb.exe"))

    if android_sdk:
        candidates.append(os.path.join(android_sdk,
            "platform-tools", "adb.exe"))

    # Типичные пути на случай нестандартной установки
    candidates += [
        r"C:\Android\platform-tools\adb.exe",
        r"C:\android-sdk\platform-tools\adb.exe",
        os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
        os.path.expanduser(r"~\Android\Sdk\platform-tools\adb.exe"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


ADB = find_adb()


def run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_adb() -> bool:
    if ADB is None:
        print("❌  adb не найден.")
        print()
        print("    Варианты решения:")
        print("    1) Установите Android Studio — sdk будет в:")
        print(r"       %LOCALAPPDATA%\Android\Sdk\platform-tools" + "\\")
        print()
        print("    2) Или скачайте Platform Tools отдельно:")
        print("       https://developer.android.com/studio/releases/platform-tools")
        print("       и добавьте папку platform-tools в PATH")
        print()
        print("    3) Или укажите путь вручную через --adb:")
        print(r'       python revoke_permissions.py --adb "C:\path\to\adb.exe" --list')
        return False

    code, out, err = run([ADB, "version"])
    if code != 0:
        print(f"❌  adb найден по пути {ADB}, но не запускается: {err}")
        return False

    print(f"adb: {ADB}")
    print(f"    {out.splitlines()[0]}")
    return True


# ---------------------------------------------------------------
# Работа с устройствами
# ---------------------------------------------------------------

def get_connected_devices() -> list[str]:
    _, out, _ = run([ADB, "devices"])
    lines = out.splitlines()[1:]
    return [l.split("\t")[0] for l in lines if "\tdevice" in l]


def get_permission_status(package: str, permission: str, device: str) -> str:
    _, out, _ = run([ADB, "-s", device, "shell", "dumpsys", "package", package])
    for line in out.splitlines():
        if permission in line:
            if "granted=true"  in line: return "GRANTED"
            if "granted=false" in line: return "DENIED"
    return "UNKNOWN"


def revoke_permission(package: str, permission: str, device: str) -> bool:
    code, _, _ = run([ADB, "-s", device, "shell", "pm", "revoke", package, permission])
    return code == 0


def grant_permission(package: str, permission: str, device: str) -> bool:
    code, _, _ = run([ADB, "-s", device, "shell", "pm", "grant", package, permission])
    return code == 0


# ---------------------------------------------------------------
# Команды
# ---------------------------------------------------------------

def cmd_list(package: str, device: str):
    print(f"\nПакет     : {package}")
    print(f"Устройство: {device}\n")
    print(f"  {'Ключ':<12} {'Разрешение':<45} Статус")
    print("  " + "-" * 72)
    for key, perm in PERMISSIONS.items():
        status = get_permission_status(package, perm, device)
        icon = {"GRANTED": "🟢", "DENIED": "🔴", "UNKNOWN": "⚪"}.get(status, "⚪")
        print(f"  {key:<12} {perm:<45} {icon}  {status}")
    print()


def cmd_revoke(package: str, device: str, target: str | None):
    targets = _resolve_target(target)
    print(f"\nПакет     : {package}")
    print(f"Устройство: {device}\n")
    for key, perm in targets.items():
        before = get_permission_status(package, perm, device)
        if before != "GRANTED":
            print(f"  ⚪  {key}: уже не выдано ({before}), пропускаем")
            continue
        ok    = revoke_permission(package, perm, device)
        after = get_permission_status(package, perm, device)
        if ok and after != "GRANTED":
            print(f"  ✅  {key}: снято  ({before} → {after})")
        else:
            print(f"  ❌  {key}: не удалось снять")
    print()


def cmd_grant(package: str, device: str, target: str | None):
    targets = _resolve_target(target)
    print(f"\nПакет     : {package}")
    print(f"Устройство: {device}\n")
    for key, perm in targets.items():
        ok    = grant_permission(package, perm, device)
        after = get_permission_status(package, perm, device)
        if ok and after == "GRANTED":
            print(f"  ✅  {key}: выдано")
        else:
            print(f"  ❌  {key}: не удалось выдать")
    print()


def _resolve_target(target: str | None) -> dict[str, str]:
    if target is None:
        return PERMISSIONS
    key = target.upper()
    if key not in PERMISSIONS:
        print(f"❌  Неизвестное разрешение: {target}")
        print(f"    Доступные: {', '.join(PERMISSIONS.keys())}")
        sys.exit(1)
    return {key: PERMISSIONS[key]}


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Управление runtime-разрешениями Android через adb"
    )
    parser.add_argument("--package",    default=DEFAULT_PACKAGE)
    parser.add_argument("--device",     default=None)
    parser.add_argument("--permission", default=None,
                        help=f"Одно из: {', '.join(PERMISSIONS.keys())}")
    parser.add_argument("--adb",        default=None,
                        help="Явный путь к adb.exe, если не найден автоматически")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--revoke", action="store_true", help="Снять разрешения (по умолчанию)")
    group.add_argument("--grant",  action="store_true", help="Выдать разрешения")
    group.add_argument("--list",   action="store_true", help="Показать статусы")

    args = parser.parse_args()

    # Позволяем передать путь к adb вручную
    global ADB
    if args.adb:
        if not os.path.isfile(args.adb):
            print(f"❌  Файл не найден: {args.adb}")
            sys.exit(1)
        ADB = args.adb

    if not check_adb():
        sys.exit(1)

    devices = get_connected_devices()
    if not devices:
        print("\n❌  Нет подключённых устройств.")
        print("    Убедитесь, что:")
        print("    • USB Debugging включён (Настройки → Для разработчиков)")
        print("    • Кабель подключён и телефон разблокирован")
        print("    • На телефоне подтверждён запрос 'Разрешить отладку по USB'")
        sys.exit(1)

    device = args.device
    if not device:
        if len(devices) > 1:
            print(f"⚠️  Подключено несколько устройств: {devices}")
            print("    Укажите нужное через --device <serial>")
            sys.exit(1)
        device = devices[0]

    if args.list:
        cmd_list(args.package, device)
    elif args.grant:
        cmd_grant(args.package, device, args.permission)
    else:
        cmd_revoke(args.package, device, args.permission)


if __name__ == "__main__":
    main()
