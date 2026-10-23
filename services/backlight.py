"""螢幕背光（sysfs）：自動找裝置，百分比與原始值互換。

原本設定頁寫死 `/sys/class/backlight/11-0045`，那是最早那片螢幕的路徑；
118 的螢幕是 `panel_backlight@1`，亮度滑桿因此完全沒作用（2026-10-23）。
現在改成掃 `/sys/class/backlight/` 下第一個有 `brightness` 與 `max_brightness`
的裝置，並依該裝置的 `max_brightness` 換算。

0% 不是全黑：底線是 max 的 8/31，沿用原本 8～31 的對應，避免螢幕暗到看不見。
max 為 31 時換算結果與原本完全相同。

只依賴 stdlib，**不 import Kivy**，方便測試。
"""
import os

BACKLIGHT_ROOT = '/sys/class/backlight'
DEFAULT_PERCENT = 50


def find_backlight(root=BACKLIGHT_ROOT):
    """回傳第一個可用背光裝置的目錄；沒有則回傳 None（例如 HDMI 螢幕）。"""
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    for name in names:
        path = os.path.join(root, name)
        if (os.path.isfile(os.path.join(path, 'brightness'))
                and os.path.isfile(os.path.join(path, 'max_brightness'))):
            return path
    return None


def _floor(max_raw):
    return round(max_raw * 8 / 31)


def percent_to_raw(percent, max_raw):
    percent = max(0, min(100, int(percent)))
    floor = _floor(max_raw)
    return int(floor + (percent / 100.0) * (max_raw - floor))


def raw_to_percent(raw, max_raw):
    floor = _floor(max_raw)
    if raw <= floor:
        return 0
    if raw >= max_raw:
        return 100
    return int(((raw - floor) / (max_raw - floor)) * 100)


def _read_int(path):
    with open(path, 'r') as f:
        return int(f.read().strip())


def read_percent(root=BACKLIGHT_ROOT):
    """目前亮度的百分比；找不到裝置時回傳 None。"""
    device = find_backlight(root)
    if device is None:
        return None
    max_raw = _read_int(os.path.join(device, 'max_brightness'))
    return raw_to_percent(_read_int(os.path.join(device, 'brightness')), max_raw)


def write_percent(percent, root=BACKLIGHT_ROOT):
    """設定亮度；回傳 (裝置目錄, 寫入的原始值, max)，找不到裝置時回傳 None。

    沒有寫入權限時丟 PermissionError（使用者需在 video 群組）。
    """
    device = find_backlight(root)
    if device is None:
        return None
    max_raw = _read_int(os.path.join(device, 'max_brightness'))
    raw = percent_to_raw(percent, max_raw)
    with open(os.path.join(device, 'brightness'), 'w') as f:
        f.write(str(raw))
    return device, raw, max_raw
