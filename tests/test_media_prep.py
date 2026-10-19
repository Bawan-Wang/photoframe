import os
import subprocess

import pytest
from PIL import Image as PILImage

from services import media_prep
from tests.conftest import make_exif_rotated_jpeg, make_jpeg, needs_heif_convert, set_mtime


def test_exif_orientation_is_applied(tmp_path):
    src = make_exif_rotated_jpeg(str(tmp_path / 'a.jpg'), (400, 200))
    dst = str(tmp_path / 'out.jpg')
    media_prep.prepare_image(src, dst)
    with PILImage.open(dst) as img:
        assert img.size == (200, 400)


def test_large_image_is_shrunk_keeping_ratio(tmp_path):
    src = make_jpeg(str(tmp_path / 'big.jpg'), (4000, 3000))
    dst = str(tmp_path / 'out.jpg')
    media_prep.prepare_image(src, dst)
    with PILImage.open(dst) as img:
        assert img.size == (1440, 1080)


def test_small_image_is_not_enlarged(tmp_path):
    src = make_jpeg(str(tmp_path / 'small.jpg'), (300, 200))
    dst = str(tmp_path / 'out.jpg')
    media_prep.prepare_image(src, dst)
    with PILImage.open(dst) as img:
        assert img.size == (300, 200)


def test_transparent_pixels_become_black(tmp_path):
    src = str(tmp_path / 'a.png')
    img = PILImage.new('RGBA', (100, 100), (255, 255, 255, 0))
    img.paste((255, 0, 0, 255), (0, 0, 50, 100))
    img.save(src)
    dst = str(tmp_path / 'out.jpg')
    media_prep.prepare_image(src, dst)
    with PILImage.open(dst) as out:
        r, g, b = out.convert('RGB').getpixel((90, 50))
        assert max(r, g, b) < 10
        r, g, b = out.convert('RGB').getpixel((10, 50))
        assert r > 200 and g < 30


def test_is_fresh_follows_source_mtime(tmp_path):
    src = make_jpeg(str(tmp_path / 'a.jpg'))
    dst = str(tmp_path / 'out.jpg')
    assert not media_prep.is_fresh(src, dst)
    media_prep.prepare_image(src, dst)
    assert media_prep.is_fresh(src, dst)
    st = os.stat(dst)
    set_mtime(src, st.st_mtime + 10)
    assert not media_prep.is_fresh(src, dst)


def test_broken_image_raises_and_leaves_nothing(tmp_path):
    src = tmp_path / 'broken.jpg'
    src.write_bytes(b'not a jpeg at all')
    out_dir = tmp_path / 'cache'
    out_dir.mkdir()
    dst = str(out_dir / 'broken.jpg.jpg')
    with pytest.raises(Exception):
        media_prep.prepare_image(str(src), dst)
    assert os.listdir(out_dir) == []


def test_clean_partials(tmp_path):
    (tmp_path / 'a.jpg.jpg.part').write_bytes(b'x')
    (tmp_path / 'b.jpg.jpg').write_bytes(b'x')
    media_prep.clean_partials(str(tmp_path))
    assert os.listdir(tmp_path) == ['b.jpg.jpg']


def test_failed_marker_respects_source_mtime(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    src = make_jpeg(str(tmp_path / 'a.jpg'))
    assert not media_prep.has_failed(src, str(cache))
    media_prep.mark_failed(src, str(cache))
    assert media_prep.has_failed(src, str(cache))
    marker = media_prep.failed_marker(src, str(cache))
    set_mtime(src, os.stat(marker).st_mtime + 10)
    assert not media_prep.has_failed(src, str(cache))


def test_heic_without_heif_convert_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(media_prep, 'has_heif_convert', lambda: False)
    src = tmp_path / 'a.heic'
    src.write_bytes(b'whatever')
    dst = str(tmp_path / 'out.jpg')
    with pytest.raises(RuntimeError):
        media_prep.prepare_image(str(src), dst)
    assert not os.path.exists(dst)


@needs_heif_convert
def test_heic_is_converted_upright(tmp_path):
    png = make_jpeg(str(tmp_path / 'a.jpg'), (400, 200))
    heic = str(tmp_path / 'a.heic')
    subprocess.run(['heif-enc', '-o', heic, png], check=True, capture_output=True)
    dst = str(tmp_path / 'out.jpg')
    media_prep.prepare_image(heic, dst)
    with PILImage.open(dst) as img:
        assert img.size == (400, 200)


@needs_heif_convert
def test_heic_with_exif_orientation_is_rotated_once(tmp_path):
    # heif-enc 只把 EXIF Orientation 帶進 HEIC（沒有 irot），heif-convert 輸出仍是
    # 橫的並保留 Orientation=6，必須由 exif_transpose 轉正一次。
    # 真實 iPhone HEIC（irot + EXIF）無法在這裡產生，留給實機驗收
    jpg = make_exif_rotated_jpeg(str(tmp_path / 'rot.jpg'), (400, 200))
    heic = str(tmp_path / 'rot.heic')
    subprocess.run(['heif-enc', '-o', heic, jpg], check=True, capture_output=True)
    dst = str(tmp_path / 'out.jpg')
    media_prep.prepare_image(heic, dst)
    with PILImage.open(dst) as img:
        assert img.size == (200, 400)
