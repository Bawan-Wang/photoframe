import os

import pytest

from services import media_paths


class FakeMediaRoot:
    """tmp_path 底下的資料夾當成掛載點（真的 mount 需要 root）。"""

    def __init__(self, root):
        self.root = root
        self.mounts = set()

    def add(self, name, files=(), images_dir=False):
        mount = self.root / name
        mount.mkdir()
        self.mounts.add(str(mount))
        if images_dir:
            (mount / 'images').mkdir()
        for f in files:
            (mount / f).write_bytes(b'x')
        return mount

    def __str__(self):
        return str(self.root)

    def __truediv__(self, other):
        return self.root / other


@pytest.fixture
def media_root(tmp_path, monkeypatch):
    fake = FakeMediaRoot(tmp_path / 'media')
    fake.root.mkdir()
    monkeypatch.setattr(media_paths.os.path, 'ismount', lambda p: str(p) in fake.mounts)
    return fake


def test_no_media_root_returns_none(tmp_path):
    assert media_paths.find_usb_images_dir(str(tmp_path / 'missing')) is None


def test_images_subdir_wins(media_root):
    mount = media_root.add('USB', files=['a.jpg'], images_dir=True)
    assert media_paths.find_usb_images_dir(str(media_root)) == str(mount / 'images')


def test_root_with_media_is_used(media_root):
    mount = media_root.add('USB DISK', files=['IMG_1.HEIC'])
    assert media_paths.find_usb_images_dir(str(media_root)) == str(mount)


def test_root_with_only_video_is_used(media_root):
    mount = media_root.add('USB', files=['clip.mov'])
    assert media_paths.find_usb_images_dir(str(media_root)) == str(mount)


def test_empty_stick_returns_none(media_root):
    media_root.add('USB', files=['notes.txt'])
    assert media_paths.find_usb_images_dir(str(media_root)) is None


def test_plain_directory_is_not_a_mount(media_root):
    (media_root / 'leftover').mkdir()
    (media_root / 'leftover' / 'a.jpg').write_bytes(b'x')
    assert media_paths.find_usb_images_dir(str(media_root)) is None


def test_first_usable_mount_in_name_order(media_root):
    media_root.add('B', files=['b.jpg'])
    a = media_root.add('A', files=['a.jpg'])
    assert media_paths.find_usb_images_dir(str(media_root)) == str(a)


def test_media_exts_match_media_prep():
    from services import media_prep
    assert media_prep.MEDIA_EXTS == media_paths.MEDIA_EXTS
    assert media_prep.is_media('x.MP4')


def test_local_images_dir_is_photoframe_images():
    expected = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(media_paths.__file__))),
                            'images')
    assert os.path.abspath(media_paths.LOCAL_IMAGES_DIR) == expected
