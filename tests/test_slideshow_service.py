import threading
import time

import pytest

from services.slideshow_service import SlideshowService


class FakeRepo:
    def __init__(self, files):
        self.files = list(files)

    def get_image_files(self):
        return self.files


@pytest.fixture
def thread_errors():
    errors = []
    old = threading.excepthook
    threading.excepthook = lambda args: errors.append(args.exc_value)
    yield errors
    threading.excepthook = old


def _wait_until(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_photos_advance_by_interval():
    svc = SlideshowService(FakeRepo(['a', 'b', 'c']), auto_play_interval=0.1)
    svc.set_slideshow_loop(True)
    seen = []
    svc.set_image_changed_callback(seen.append)
    svc.start_auto_play()
    try:
        assert _wait_until(lambda: len(seen) >= 3)
    finally:
        svc.stop_auto_play()
    assert seen[:3] == ['b', 'c', 'a']


def test_stops_at_last_without_loop_and_no_thread_errors(thread_errors):
    svc = SlideshowService(FakeRepo(['a', 'b']), auto_play_interval=0.05)
    svc.set_slideshow_loop(False)
    svc.start_auto_play()
    assert _wait_until(lambda: not svc.is_auto_playing)
    time.sleep(0.1)
    assert svc.get_current_image() == 'b'
    assert thread_errors == []


def test_stop_returns_quickly_with_long_interval():
    svc = SlideshowService(FakeRepo(['a', 'b']), auto_play_interval=30)
    svc.start_auto_play()
    time.sleep(0.05)
    start = time.monotonic()
    svc.stop_auto_play()
    assert time.monotonic() - start < 0.5


def test_add_media_keeps_current_item():
    repo = FakeRepo(['b', 'd'])
    svc = SlideshowService(repo)
    svc.next_image()
    assert svc.get_current_image() == 'd'
    repo.files = ['a', 'b', 'c', 'd']  # repository 換一個新 list
    svc.add_media('a')
    assert svc.get_current_image() == 'd'


def test_add_media_into_empty_list_emits():
    repo = FakeRepo([])
    svc = SlideshowService(repo)
    seen = []
    svc.set_image_changed_callback(seen.append)
    repo.files = ['a']
    svc.add_media('a')
    assert seen == ['a']


def test_add_media_ignored_by_custom_playlist():
    repo = FakeRepo(['a', 'b'])
    svc = SlideshowService(repo)
    svc.set_custom_playlist(['b'])
    repo.files = ['a', 'b', 'c']
    svc.add_media('c')
    assert svc.get_current_image() == 'b'


def test_concurrent_add_media_while_playing(thread_errors):
    repo = FakeRepo(['p000'])
    svc = SlideshowService(repo, auto_play_interval=0.001)
    svc.set_slideshow_loop(True)
    svc.start_auto_play()

    def adder():
        for i in range(1, 51):
            repo.files = sorted(repo.files + [f'p{i:03d}'])
            svc.add_media(f'p{i:03d}')

    t = threading.Thread(target=adder)
    t.start()
    t.join()
    try:
        for _ in range(50):
            with svc._lock:
                assert 0 <= svc.index < len(svc.images)
            time.sleep(0.002)
    finally:
        svc.stop_auto_play()
    assert len(svc.images) == 51
    assert thread_errors == []


class PendingRepo(FakeRepo):
    def __init__(self, files):
        super().__init__(files)
        self.pending = True

    def has_pending_jobs(self):
        return self.pending


def test_no_loop_waits_at_last_while_photos_are_still_processing(thread_errors):
    # 第一次打開、照片還在背景處理時，清單只有一張；不循環也不能就此停止
    repo = PendingRepo(['a'])
    svc = SlideshowService(repo, auto_play_interval=0.05)
    svc.set_slideshow_loop(False)
    seen = []
    svc.set_image_changed_callback(seen.append)
    svc.start_auto_play()
    try:
        time.sleep(0.3)
        assert svc.is_auto_playing
        repo.files = ['a', 'b']
        svc.add_media('b')
        repo.pending = False
        assert _wait_until(lambda: 'b' in seen)
        assert _wait_until(lambda: not svc.is_auto_playing)
    finally:
        svc.stop_auto_play()
    assert svc.get_current_image() == 'b'
    assert thread_errors == []
