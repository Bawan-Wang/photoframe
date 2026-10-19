"""photoframe 測試共用設定。不依賴 Kivy，用系統 python3（apt 的 Pillow）執行：

    cd photoframe && python3 -m pytest -q tests
"""
import os
import shutil
import subprocess
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


needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None,
    reason='需要 ffmpeg／ffprobe',
)


def make_video(path, size=(320, 240), duration=1.0, fps=30, vcodec='libx264',
               pix_fmt='yuv420p', audio='aac', extra=()):
    """用 lavfi 的 testsrc／sine 產生測試影片。audio=None 表示沒有音軌。"""
    w, h = size
    args = ['ffmpeg', '-y', '-v', 'error',
            '-f', 'lavfi', '-i', f'testsrc=size={w}x{h}:rate={fps}:duration={duration}']
    if audio:
        args += ['-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration}']
    args += ['-c:v', vcodec, '-pix_fmt', pix_fmt]
    if vcodec == 'libx265':
        args += ['-x265-params', 'log-level=error']
    if audio:
        args += ['-c:a', audio]
    args += list(extra) + ['-shortest', path]
    subprocess.run(args, check=True, capture_output=True)
    return path


def make_rotated_video(path, size=(320, 240)):
    """帶 rotate=90 標記的影片。ffmpeg 5.1 沒有 -display_rotation（6.0 才有），
    改用 -metadata:s:v:0 rotate=90（ffprobe 讀得到 rotation）。"""
    plain = path + '.plain.mp4'
    make_video(plain, size)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', plain, '-c', 'copy',
                    '-metadata:s:v:0', 'rotate=90', path], check=True, capture_output=True)
    os.remove(plain)
    return path
