import threading
import time
from typing import List, Optional

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

    def refresh_images(self):
        self.images = self.image_repository.get_image_files()
        self.index = 0
        # 如果使用自定義播放列表，需要重新驗證索引
        if self.custom_playlist:
            self._validate_custom_playlist()

    def get_current_image(self):
        if not self.images:
            return ''
        
        if self.custom_playlist:
            if not self.custom_playlist or self.index >= len(self.custom_playlist):
                return ''
            return self.custom_playlist[self.index]
        
        return self.images[self.index]

    def next_image(self):
        if not self.images:
            return ''
        
        if self.custom_playlist:
            if not self.custom_playlist:
                return ''
            self.index = (self.index + 1) % len(self.custom_playlist)
        else:
            self.index = (self.index + 1) % len(self.images)
        
        current_image = self.get_current_image()
        if self.on_image_changed_callback:
            self.on_image_changed_callback(current_image)
        return current_image

    def prev_image(self):
        if not self.images:
            return ''
        
        if self.custom_playlist:
            if not self.custom_playlist:
                return ''
            self.index = (self.index - 1) % len(self.custom_playlist)
        else:
            self.index = (self.index - 1) % len(self.images)
        
        current_image = self.get_current_image()
        if self.on_image_changed_callback:
            self.on_image_changed_callback(current_image)
        return self.get_current_image()

    def set_auto_play_interval(self, interval: float):
        """設定自動播放的間隔時間（秒）"""
        self.auto_play_interval = interval
        if self.is_auto_playing:
            self.stop_auto_play()
            self.start_auto_play()

    def start_auto_play(self):
        """開始自動播放"""
        if self.is_auto_playing:
            return
        
        self.is_auto_playing = True
        self.auto_play_thread = threading.Thread(target=self._auto_play_loop, daemon=True)
        self.auto_play_thread.start()

    def stop_auto_play(self):
        """停止自動播放"""
        self.is_auto_playing = False
        if self.auto_play_thread:
            self.auto_play_thread.join(timeout=1.0)
            self.auto_play_thread = None

    def _auto_play_loop(self):
        """自動播放循環"""
        while self.is_auto_playing:
            time.sleep(self.auto_play_interval)
            if self.is_auto_playing:  # 再次檢查，避免在sleep期間被停止
                self.next_image()

    def set_custom_playlist(self, image_paths: List[str]):
        """設定自定義播放列表
        
        Args:
            image_paths: 圖片路徑列表，路徑應該是相對於images目錄的完整路徑
        """
        if not image_paths:
            self.custom_playlist = None
            self.index = 0
            return
        
        # 驗證所有路徑都存在於images中
        valid_paths = []
        for path in image_paths:
            if path in self.images:
                valid_paths.append(path)
            else:
                print(f"Warning: Image path not found: {path}")
        
        self.custom_playlist = valid_paths
        self.index = 0

    def clear_custom_playlist(self):
        """清除自定義播放列表，回到所有圖片播放模式"""
        self.custom_playlist = None
        self.index = 0

    def get_playlist_info(self):
        """獲取當前播放列表信息"""
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