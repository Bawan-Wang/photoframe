"""照片前處理：轉正方向、縮圖、寫入快取（exec-plan 042A）。

只依賴 stdlib、Pillow 與 `heif-convert` CLI，**不 import Kivy**，方便測試。
所有寫入都先寫到同目錄的 `<dst>.part` 再 `os.replace`，拔隨身碟、斷電或
相框被砍時不會留下半個檔案。
"""
import os
import shutil
import subprocess
import tempfile

from PIL import Image as PILImage
from PIL import ImageOps

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.heic', '.heif')
HEIF_EXTS = ('.heic', '.heif')
DEFAULT_MAX_IMAGE_SIZE = (1920, 1080)
THUMB_SIZE = (360, 360)
JPEG_QUALITY = 88
PART_SUFFIX = '.part'
FAILED_SUFFIX = '.failed'
HEIF_CONVERT_TIMEOUT = 120


def is_image(path):
    return path.lower().endswith(IMAGE_EXTS)


def is_heif(path):
    return path.lower().endswith(HEIF_EXTS)


def is_fresh(src, cached):
    """快取存在、非空，且不比來源舊。"""
    try:
        st = os.stat(cached)
        return st.st_size > 0 and st.st_mtime >= os.stat(src).st_mtime
    except OSError:
        return False


def failed_marker(src, cache_dir):
    return os.path.join(cache_dir, os.path.basename(src) + FAILED_SUFFIX)


def has_failed(src, cache_dir):
    """標記檔比來源新就不再重試；來源被換掉（mtime 變新）就重試。"""
    marker = failed_marker(src, cache_dir)
    try:
        return os.stat(marker).st_mtime >= os.stat(src).st_mtime
    except OSError:
        return False


def mark_failed(src, cache_dir):
    try:
        with open(failed_marker(src, cache_dir), 'w', encoding='utf-8'):
            pass
    except OSError as e:
        print(f"無法寫入失敗標記 {src}: {e}")


def clean_partials(cache_dir):
    """刪除上次中斷留下的 *.part。"""
    try:
        names = os.listdir(cache_dir)
    except OSError:
        return
    for name in names:
        if name.endswith(PART_SUFFIX):
            try:
                os.remove(os.path.join(cache_dir, name))
            except OSError:
                pass


def has_heif_convert():
    return shutil.which('heif-convert') is not None


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _open_heif(src):
    """HEIC 用 heif-convert 轉成暫存 JPEG，回傳暫存檔路徑（呼叫端負責刪除）。

    bookworm 的 apt 沒有 pillow_heif，Pillow 9.4 也讀不了 HEIC，只能走這條路。
    """
    if not has_heif_convert():
        raise RuntimeError("沒有 heif-convert，無法讀取 HEIC（請 apt install libheif-examples）")
    fd, tmp = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)
    try:
        subprocess.run(
            ['heif-convert', '-q', '95', src, tmp],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=HEIF_CONVERT_TIMEOUT,
        )
        if os.path.getsize(tmp) == 0:
            raise RuntimeError(f"heif-convert 輸出為空: {src}")
    except Exception:
        _remove_quietly(tmp)
        raise
    return tmp


def _to_rgb_on_black(img):
    """透明或調色盤模式貼到黑底上，透明處才會是黑色而不是隨機顏色。"""
    if img.mode in ('RGB', 'L'):
        return img
    rgba = img.convert('RGBA')
    background = PILImage.new('RGB', rgba.size, (0, 0, 0))
    background.paste(rgba, mask=rgba.getchannel('A'))
    return background


def prepare_image(src, dst, max_size=DEFAULT_MAX_IMAGE_SIZE):
    """把 src 轉正方向、縮到 max_size 以內（只縮不放），存成 JPEG 到 dst。

    失敗時丟例外，且不留下 dst、.part 或 HEIC 暫存檔。
    """
    heif_tmp = _open_heif(src) if is_heif(src) else None
    part = dst + PART_SUFFIX
    try:
        with PILImage.open(heif_tmp or src) as img:
            if img.format == 'JPEG':
                # 讓解碼器直接縮小 2 的次方倍，大圖快好幾倍；用正方形上限，
                # 之後轉 90 度時尺寸才不會不夠
                side = max(max_size)
                img.draft('RGB', (side, side))
            img = ImageOps.exif_transpose(img)
            img = _to_rgb_on_black(img)
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            img.save(part, 'JPEG', quality=JPEG_QUALITY)
        os.replace(part, dst)
    except Exception:
        _remove_quietly(part)
        raise
    finally:
        if heif_tmp:
            _remove_quietly(heif_tmp)
    return dst
