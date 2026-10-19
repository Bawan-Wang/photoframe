import os

from repositories.image_repository import ImageRepository
from services import media_prep
from tests.conftest import make_jpeg, make_video, needs_ffmpeg

pytestmark = needs_ffmpeg


def _images(tmp_path):
    d = tmp_path / 'images'
    d.mkdir(exist_ok=True)
    return d


def _repo(tmp_path):
    return ImageRepository(str(_images(tmp_path)), str(tmp_path / 'thumbnails'), background=False)


def _names(repo):
    return [os.path.basename(repo.get_original_image_path(p)) for p in repo.get_image_files()]


def test_compatible_video_uses_original_and_gets_poster(tmp_path):
    d = _images(tmp_path)
    src = make_video(str(d / 'clip.mp4'))
    repo = _repo(tmp_path)
    assert repo.get_image_files() == []  # 先 probe，不在掃描時做
    repo.process_pending()
    assert repo.get_image_files() == [src]
    assert repo.is_video(src)
    poster = repo.get_thumbnail(src)
    assert poster and poster.endswith('.poster.jpg') and os.path.exists(poster)


def test_large_playable_video_plays_original_then_is_replaced(tmp_path):
    d = _images(tmp_path)
    make_jpeg(str(d / 'a.jpg'))
    src = make_video(str(d / 'b.mp4'), size=(1280, 800))
    make_jpeg(str(d / 'c.jpg'))
    repo = _repo(tmp_path)
    seen = []
    repo.add_listener(seen.append)
    repo.get_image_files()

    repo.process_pending(max_jobs=3)  # 兩張照片 + 影片 probe；轉檔還沒做
    before = repo.get_image_files()
    assert _names(repo) == ['a.jpg', 'b.mp4', 'c.jpg']
    assert before[1] == src  # 先播原檔
    assert repo.has_pending_jobs()
    assert not repo.expects_more_items()  # 只剩把原檔換成 720p，不會再增加項目

    repo.process_pending()
    after = repo.get_image_files()
    assert after is not before and before[1] == src  # 舊 list 沒被改
    assert after[1].endswith('b.mp4.mp4') and after[1] != src  # 原位換成轉檔結果
    assert _names(repo) == ['a.jpg', 'b.mp4', 'c.jpg']
    assert seen[-1] == after[1]
    info = media_prep.probe(after[1])
    assert (info['width'], info['height']) == (1152, 720)
    assert repo.get_thumbnail(after[1]).endswith('.poster.jpg')


def test_unplayable_video_appears_only_after_transcode(tmp_path):
    d = _images(tmp_path)
    make_video(str(d / 'h.mov'), vcodec='libx265', pix_fmt='yuv420p10le')
    repo = _repo(tmp_path)
    repo.get_image_files()
    repo.process_pending(max_jobs=1)  # probe
    assert repo.get_image_files() == []
    assert repo.expects_more_items()
    repo.process_pending()
    files = repo.get_image_files()
    assert len(files) == 1 and files[0].endswith('h.mov.mp4')
    assert media_prep.video_is_compatible(media_prep.probe(files[0]))


def test_new_repository_reuses_transcode_cache(tmp_path):
    d = _images(tmp_path)
    make_video(str(d / 'h.mov'), vcodec='libx265', pix_fmt='yuv420p10le')
    first = _repo(tmp_path)
    first.get_image_files()
    first.process_pending()

    second = _repo(tmp_path)
    files = second.get_image_files()
    assert len(files) == 1 and files[0].endswith('h.mov.mp4')
    assert not second.has_pending_jobs()


def test_broken_video_is_marked_and_skipped(tmp_path):
    d = _images(tmp_path)
    (d / 'broken.mp4').write_text('not a video')
    first = _repo(tmp_path)
    first.get_image_files()
    first.process_pending()
    assert first.get_image_files() == []
    assert os.path.exists(os.path.join(first.cache_dir, 'broken.mp4' + media_prep.FAILED_SUFFIX))

    second = _repo(tmp_path)
    assert second.get_image_files() == []
    assert not second.has_pending_jobs()


def test_live_photo_movie_is_skipped(tmp_path):
    d = _images(tmp_path)
    make_jpeg(str(d / 'IMG_1.JPG'))
    make_video(str(d / 'IMG_1.MOV'))
    make_video(str(d / 'IMG_2.MOV'))
    repo = _repo(tmp_path)
    repo.get_image_files()
    repo.process_pending()
    assert _names(repo) == ['IMG_1.JPG', 'IMG_2.MOV']


def test_order_follows_original_names(tmp_path):
    d = _images(tmp_path)
    make_video(str(d / '00_hevc.mov'), vcodec='libx265', pix_fmt='yuv420p10le')
    make_jpeg(str(d / '01_photo.jpg'))
    make_video(str(d / '02_clip.mp4'))
    make_jpeg(str(d / '03_photo.png'))
    repo = _repo(tmp_path)
    repo.get_image_files()
    repo.process_pending()
    assert _names(repo) == ['00_hevc.mov', '01_photo.jpg', '02_clip.mp4', '03_photo.png']


def test_without_ffmpeg_video_uses_original(tmp_path):
    d = _images(tmp_path)
    src = make_video(str(d / 'clip.mov'), vcodec='libx265', pix_fmt='yuv420p10le')
    repo = _repo(tmp_path)
    repo.has_ffmpeg = False
    assert repo.get_image_files() == [src]
    assert not repo.has_pending_jobs()
    assert repo.get_thumbnail(src) is None


def test_failed_transcode_of_playable_video_keeps_original(tmp_path, monkeypatch):
    d = _images(tmp_path)
    src = make_video(str(d / 'b.mp4'), size=(1280, 800))

    def boom(*args, **kwargs):
        raise RuntimeError('disk full')

    monkeypatch.setattr(media_prep, 'transcode_video', boom)
    first = _repo(tmp_path)
    first.get_image_files()
    first.process_pending()
    assert first.get_image_files() == [src]
    assert os.path.exists(os.path.join(first.cache_dir, 'b.mp4' + media_prep.TRANSCODE_FAILED_SUFFIX))

    second = _repo(tmp_path)
    second.get_image_files()
    second.process_pending()
    assert second.get_image_files() == [src]  # 原檔照播，不再重試轉檔


def test_shutdown_cancels_running_transcode_and_cleans_part(tmp_path):
    import time

    d = _images(tmp_path)
    # 60 fps：播得動但要轉檔（產生 H.264 比 HEVC 快得多）
    make_video(str(d / 'long.mov'), size=(1280, 720), duration=10, fps=60, audio=None,
               extra=('-preset', 'ultrafast'))
    repo = ImageRepository(str(d), str(tmp_path / 'thumbnails'), background=True)
    repo.get_image_files()
    part = os.path.join(repo.cache_dir, 'long.mov.mp4' + media_prep.PART_SUFFIX)
    end = time.monotonic() + 20
    while not os.path.exists(part) and time.monotonic() < end:
        time.sleep(0.1)
    assert os.path.exists(part), '轉檔沒有開始'
    start = time.monotonic()
    repo.shutdown()
    assert time.monotonic() - start < 2.5
    assert not os.path.exists(part)
    assert not os.path.exists(os.path.join(repo.cache_dir, 'long.mov' + media_prep.FAILED_SUFFIX))
