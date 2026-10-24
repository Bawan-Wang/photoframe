"""照片與影片放在哪裡、哪些副檔名算媒體檔。

**只依賴 stdlib**，也不 import 本專案的其他模組：上層 repo 的上傳功能（exec-plan 044）
用檔案路徑直接載入這個模組，在沒有 Pillow 的 `.venv` 裡也要能用。相框與上傳共用
同一個 `find_usb_images_dir()`，上傳存進去的照片相框才一定看得到。
"""
import getpass
import os

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.heic', '.heif')
VIDEO_EXTS = ('.mp4', '.mov', '.m4v', '.avi', '.mkv', '.3gp', '.mts', '.webm')
MEDIA_EXTS = IMAGE_EXTS + VIDEO_EXTS

# 沒有隨身碟時的本地路徑
LOCAL_IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')


def find_usb_images_dir(media_root=None):
    """在 /media/<目前使用者>/ 底下找隨身碟的照片資料夾，找不到回傳 None。

    隨身碟裡有 images/ 子資料夾就用它，否則用隨身碟最上層（要有照片或影片才算）。
    """
    if media_root is None:
        media_root = os.path.join('/media', getpass.getuser())
    try:
        mounts = sorted(os.listdir(media_root))
    except OSError:
        return None
    for name in mounts:
        mount = os.path.join(media_root, name)
        if not os.path.ismount(mount):
            continue
        images = os.path.join(mount, 'images')
        if os.path.isdir(images):
            return images
        try:
            if any(f.lower().endswith(MEDIA_EXTS) for f in os.listdir(mount)):
                return mount
        except OSError:
            continue
    return None
