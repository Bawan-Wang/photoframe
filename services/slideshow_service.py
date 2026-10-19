import threading
import time
from typing import List, Optional

from services.media_prep import is_video

# 影片要播完才切換；eos 事件遺失時的保險上限
MAX_VIDEO_WAIT = 30 * 60

class SlideshowService:
    def __init__(self, image_repository, auto_play_interval: float = 3.0):
        self.image_repository = image_repository
        self.images = self.image_repository.get_image_files()
        self.index = 0
        self.auto_play_interval = auto_play_interval
        self.is_auto_playing = False
        self.auto_play_thread = None
        self.custom_playlist = None
        self.on_image_changed_callback = None
        self.slideshow_loop = False  # 添加循环播放状态
        self.has_played_once = False  # 标记是否已经播放过一次
        # add_media 由 repository 的背景執行緒呼叫，自動播放執行緒和 UI 執行緒
        # 也會改 index，三方都要經過這把鎖
        self._lock = threading.RLock()
        # 自動播放用 Event 等待而不是 sleep，stop 時才能立即喚醒
        self._wake = threading.Event()
        self._item_started = time.monotonic()
        self._video_done = False

    def refresh_images(self):
        with self._lock:
            self.images = self.image_repository.get_image_files()
            self.index = 0
            self.has_played_once = False  # 重置播放状态
            # 如果使用自定義播放列表，需要重新驗證索引
            if self.custom_playlist:
                self._validate_custom_playlist()

    def _current_list(self):
        return self.custom_playlist if self.custom_playlist else self.images

    def get_current_image(self):
        with self._lock:
            current_list = self._current_list()
            if not current_list or self.index >= len(current_list):
                return ''
            return current_list[self.index]

    def _emit_changed(self):
        """重設這一項的開始時間並通知 UI（callback 在鎖外呼叫）"""
        with self._lock:
            self._item_started = time.monotonic()
            self._video_done = False
            current_image = self.get_current_image()
        if self.on_image_changed_callback:
            self.on_image_changed_callback(current_image)
        return current_image

    def next_image(self):
        stop_at = None  # 不循環播到最後一張時要停在這張
        with self._lock:
            current_list = self._current_list()
            if not current_list:
                return ''

            # 检查是否到达最后一张
            if self.index >= len(current_list) - 1:
                # 到达最后一张
                if self.slideshow_loop:
                    # 循环播放：回到第一张
                    self.index = 0
                    self.has_played_once = True
                    print("循环播放：回到第一张图片")
                else:
                    # 不循环：停留在最后一张
                    stop_at = current_list[self.index]
            else:
                # 未到达最后一张，继续下一张
                self.index += 1
                # 检查是否已经播放过一次
                if self.index == len(current_list) - 1:
                    self.has_played_once = True

        if stop_at is not None:
            # 在鎖外停止自動播放：stop_auto_play 可能要 join 播放執行緒
            if self.is_auto_playing:
                self.stop_auto_play()
                print("播放完成，已停止自动播放")
            return stop_at  # 返回最后一张
        return self._emit_changed()

    def prev_image(self):
        with self._lock:
            current_list = self._current_list()
            if not current_list:
                return ''
            self.index = (self.index - 1) % len(current_list)

        return self._emit_changed()

    def add_media(self, path):
        """repository 背景處理好一項時呼叫：更新清單，畫面維持在原本正在播的項目。

        有自訂播放清單時不受影響（清單是使用者勾的）。
        """
        with self._lock:
            new_images = self.image_repository.get_image_files()
            if self.custom_playlist:
                self.images = new_images
                return
            current = self.get_current_image()
            self.images = new_images
            if current and current in new_images:
                self.index = new_images.index(current)
                return
            was_empty = not current
            if self.index >= len(new_images):
                self.index = 0
        if was_empty and new_images:
            # 原本沒有東西可播（照片都還在背景處理），現在第一張出來了
            self._emit_changed()

    def set_auto_play_interval(self, interval: float):
        """設定自動播放的間隔時間（秒）"""
        self.auto_play_interval = interval
        if self.is_auto_playing:
            self.stop_auto_play()
            self.start_auto_play()

    def set_slideshow_loop(self, loop: bool):
        """設定循環播放狀態"""
        self.slideshow_loop = loop
        print(f"循环播放设置已更新: {'开启' if loop else '关闭'}")

    def get_slideshow_loop(self) -> bool:
        """獲取循環播放狀態"""
        return self.slideshow_loop

    def start_auto_play(self):
        """開始自動播放"""
        if self.is_auto_playing:
            return

        self.is_auto_playing = True
        self.has_played_once = False  # 重置播放状态
        self._wake.clear()
        self._item_started = time.monotonic()
        self.auto_play_thread = threading.Thread(target=self._auto_play_loop, daemon=True)
        self.auto_play_thread.start()

    def stop_auto_play(self):
        """停止自動播放"""
        self.is_auto_playing = False
        self._wake.set()  # 讓等待中的播放執行緒立即醒來
        thread = self.auto_play_thread
        self.auto_play_thread = None
        # 播到最後一張時，是播放執行緒自己經由 next_image() 呼叫到這裡；
        # join 自己會丟 RuntimeError
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def _current_is_playing_video(self):
        current = self.get_current_image()
        return bool(current) and is_video(current) and not self._video_done

    def _wait_seconds(self):
        if self._current_is_playing_video():
            # 影片播完會由 notify_video_finished 喚醒；這裡只是保險的輪詢間隔
            return 1.0
        elapsed = time.monotonic() - self._item_started
        return max(0.05, self.auto_play_interval - elapsed)

    def _should_advance(self):
        elapsed = time.monotonic() - self._item_started
        current = self.get_current_image()
        if current and is_video(current):
            return self._video_done or elapsed >= MAX_VIDEO_WAIT
        return elapsed >= self.auto_play_interval

    def notify_video_finished(self, path=None):
        """UI 的影片播完（或載入逾時被跳過）時呼叫；不是目前項目的舊事件會被忽略"""
        with self._lock:
            if path is not None and path != self.get_current_image():
                return
            self._video_done = True
        self._wake.set()

    def _auto_play_loop(self):
        """自動播放循環"""
        while self.is_auto_playing:
            self._wake.wait(self._wait_seconds())
            self._wake.clear()
            if not self.is_auto_playing:  # 再次檢查，避免在等待期間被停止
                break
            with self._lock:
                current_list = self._current_list()
                if not current_list:
                    # 清單還是空的（照片都在背景處理），重新計時，不要空轉
                    self._item_started = time.monotonic()
                    continue
            if not self._should_advance():
                continue
            if self._waiting_for_more():
                # 第一次打開時照片還在背景處理，最後一張不是真的最後一張
                self._item_started = time.monotonic()
                continue
            # 不循環時 next_image() 在最後一張會自己停止自動播放
            self.next_image()

    def _waiting_for_more(self):
        """不循環、停在目前最後一張，但 repository 還有照片在處理中"""
        if self.slideshow_loop or self.custom_playlist:
            return False
        with self._lock:
            at_last = self.index >= len(self.images) - 1
        expects_more = getattr(self.image_repository, 'expects_more_items', None)
        return at_last and bool(expects_more and expects_more())

    def set_custom_playlist(self, image_paths: List[str]):
        """設定自定義播放列表

        Args:
            image_paths: 圖片路徑列表，路徑應該是相對於images目錄的完整路徑
        """
        with self._lock:
            if not image_paths:
                self.custom_playlist = None
                self.index = 0
                return

            # 直接使用传入的图片路径，不需要验证是否存在于self.images中
            # 因为播放列表传递的是完整路径，这些路径是有效的
            self.custom_playlist = image_paths
            self.index = 0

    def clear_custom_playlist(self):
        """清除自定義播放列表，回到所有圖片播放模式"""
        with self._lock:
            self.custom_playlist = None
            self.index = 0

    def get_playlist_info(self):
        """獲取當前播放列表信息"""
        with self._lock:
            if self.custom_playlist:
                return {
                    'type': 'custom',
                    'total': len(self.custom_playlist),
                    'current': self.index + 1,
                    'playlist': self.custom_playlist
                }
            else:
                return {
                    'type': 'all',
                    'total': len(self.images),
                    'current': self.index + 1,
                    'playlist': self.images
                }

    def _validate_custom_playlist(self):
        """驗證自定義播放列表的有效性"""
        if not self.custom_playlist:
            return

        # 檢查播放列表中的圖片是否仍然存在
        valid_paths = [path for path in self.custom_playlist if path in self.images]
        if len(valid_paths) != len(self.custom_playlist):
            print("Warning: Some images in custom playlist no longer exist")
            self.custom_playlist = valid_paths

        # 調整索引
        if self.custom_playlist and self.index >= len(self.custom_playlist):
            self.index = 0

    def set_image_changed_callback(self, callback):
        """設定圖片改變時的回調函數"""
        self.on_image_changed_callback = callback
