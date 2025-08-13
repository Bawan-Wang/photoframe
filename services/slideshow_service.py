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
        self.slideshow_loop = False  # 添加循环播放状态
        self.has_played_once = False  # 标记是否已经播放过一次

    def refresh_images(self):
        self.images = self.image_repository.get_image_files()
        self.index = 0
        self.has_played_once = False  # 重置播放状态
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
        
        current_list = self.custom_playlist if self.custom_playlist else self.images
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
                # 不循环：停留在最后一张，停止自动播放
                if self.is_auto_playing:
                    self.stop_auto_play()
                    print("播放完成，已停止自动播放")
                return current_list[self.index]  # 返回最后一张
        else:
            # 未到达最后一张，继续下一张
            self.index += 1
            # 检查是否已经播放过一次
            if self.index == len(current_list) - 1:
                self.has_played_once = True
        
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
                # 检查是否应该继续播放
                current_list = self.custom_playlist if self.custom_playlist else self.images
                if not current_list:
                    continue
                
                # 如果到达最后一张且不循环，停止自动播放
                if self.index >= len(current_list) - 1 and not self.slideshow_loop:
                    if self.has_played_once:
                        print("播放完成，停止自动播放")
                        # 只设置标志，不调用stop_auto_play避免线程join错误
                        self.is_auto_playing = False
                        break
                    else:
                        # 第一次到达最后一张，标记为已播放一次
                        self.has_played_once = True
                        self.next_image()
                else:
                    # 继续播放下一张
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
        
        # 直接使用传入的图片路径，不需要验证是否存在于self.images中
        # 因为播放列表传递的是完整路径，这些路径是有效的
        self.custom_playlist = image_paths
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