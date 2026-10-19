"""photoframe 測試共用設定。不依賴 Kivy，用系統 python3（apt 的 Pillow）執行：

    cd photoframe && python3 -m pytest -q tests
"""
import os
import shutil
import sys

import pytest
from PIL import Image as PILImage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

needs_heif_convert = pytest.mark.skipif(
    shutil.which('heif-convert') is None or shutil.which('heif-enc') is None,
    reason='需要 libheif-examples（heif-convert、heif-enc）',
)

EXIF_ORIENTATION = 0x0112


def make_jpeg(path, size=(400, 200), color=(200, 30, 30)):
    PILImage.new('RGB', size, color).save(path, 'JPEG')
    return path


def make_exif_rotated_jpeg(path, size=(400, 200)):
    """存一張 Orientation=6（要順時針轉 90 度才會正）的 JPEG。"""
    img = PILImage.new('RGB', size, (200, 30, 30))
    exif = img.getexif()
    exif[EXIF_ORIENTATION] = 6
    img.save(path, 'JPEG', exif=exif.tobytes())
    return path


def set_mtime(path, mtime):
    os.utime(path, (mtime, mtime))
