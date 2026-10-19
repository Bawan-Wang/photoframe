import os

from PIL import Image as PILImage

from repositories.image_repository import ImageRepository
from services import media_prep
from tests.conftest import make_exif_rotated_jpeg, make_jpeg


def _repo(tmp_path):
    images = tmp_path / 'images'
    images.mkdir(exist_ok=True)
    return ImageRepository(str(images), str(tmp_path / 'thumbnails'), background=False)


def _images(tmp_path):
    d = tmp_path / 'images'
    d.mkdir(exist_ok=True)
    return d


def test_skips_dot_files_broken_and_non_images(tmp_path):
    d = _images(tmp_path)
    make_jpeg(str(d / 'ok.jpg'))
    make_jpeg(str(d / '._ok.jpg'))
    (d / 'broken.jpg').write_bytes(b'nope')
    (d / 'notes.txt').write_text('hi')
    (d / 'sub.jpg').mkdir()
    repo = _repo(tmp_path)
    repo.get_image_files()
    repo.process_pending()
    files = repo.get_image_files()
    assert [repo.get_original_image_path(p) for p in files] == [str(d / 'ok.jpg')]


def test_gif_keeps_original(tmp_path):
    d = _images(tmp_path)
    gif = str(d / 'a.gif')
    PILImage.new('P', (50, 50)).save(gif)
    repo = _repo(tmp_path)
    assert repo.get_image_files() == [gif]
    repo.process_pending()
    thumb = repo.get_thumbnail(gif)
    assert thumb != gif and os.path.exists(thumb)


def test_photo_appears_after_background_processing(tmp_path):
    d = _images(tmp_path)
    src = make_exif_rotated_jpeg(str(d / 'a.jpg'), (400, 200))
    repo = _repo(tmp_path)
    seen = []
    repo.add_listener(seen.append)

    before = repo.get_image_files()
    assert before == []
    assert repo.has_pending_jobs()

    repo.process_pending()
    after = repo.get_image_files()
    assert len(after) == 1
    assert after is not before and before == []  # 舊 list 物件沒被改
    assert seen == after
    assert repo.get_original_image_path(after[0]) == src
    with PILImage.open(after[0]) as img:
        assert img.size == (200, 400)
    assert repo.get_thumbnail(after[0]).endswith('.thumb.jpg')
    assert not repo.has_pending_jobs()


def test_fresh_cache_is_ready_immediately(tmp_path):
    d = _images(tmp_path)
    make_jpeg(str(d / 'a.jpg'))
    first = _repo(tmp_path)
    first.get_image_files()
    first.process_pending()

    second = _repo(tmp_path)
    files = second.get_image_files()
    assert len(files) == 1
    assert not second.has_pending_jobs()
    assert second.get_thumbnail(files[0]).endswith('.thumb.jpg')


def test_broken_image_is_marked_and_not_retried(tmp_path):
    d = _images(tmp_path)
    (d / 'broken.jpg').write_bytes(b'nope')
    first = _repo(tmp_path)
    first.get_image_files()
    first.process_pending()
    assert os.path.exists(os.path.join(first.cache_dir, 'broken.jpg' + media_prep.FAILED_SUFFIX))

    second = _repo(tmp_path)
    assert second.get_image_files() == []
    assert not second.has_pending_jobs()


def test_order_follows_original_names(tmp_path):
    d = _images(tmp_path)
    make_jpeg(str(d / '03_c.png'))
    PILImage.new('P', (20, 20)).save(str(d / '02_b.gif'))
    make_jpeg(str(d / '01_a.jpg'))
    repo = _repo(tmp_path)
    repo.get_image_files()
    repo.process_pending()
    names = [os.path.basename(repo.get_original_image_path(p)) for p in repo.get_image_files()]
    assert names == ['01_a.jpg', '02_b.gif', '03_c.png']


def test_partials_are_cleaned_on_scan(tmp_path):
    _images(tmp_path)
    repo = _repo(tmp_path)
    leftover = os.path.join(repo.cache_dir, 'x.jpg.jpg.part')
    with open(leftover, 'wb') as f:
        f.write(b'x')
    repo.get_image_files()
    assert not os.path.exists(leftover)


def test_cache_lives_in_v2(tmp_path):
    _images(tmp_path)
    repo = _repo(tmp_path)
    assert repo.cache_dir == str(tmp_path / 'thumbnails' / 'v2')
