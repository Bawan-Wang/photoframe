import os
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.clock import Clock
from services.service_manager import ServiceManager

IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')

class SlideshowScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service_manager = ServiceManager()
        self.service = self.service_manager.get_slideshow_service()
        self.selected_images = None  # 存儲選中的圖片列表

        layout = FloatLayout()

        self.img_widget = Image(
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        layout.add_widget(self.img_widget)

        # --- UI container for all buttons ---
        from kivy.uix.widget import Widget
        from kivy.clock import Clock
        self.ui_container = FloatLayout(size_hint=(1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.5})

        # Back button with icon - consistent with playlist_page.py
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'back_button.png')
        if os.path.exists(icon_path):
            # Use the icon as button background for better click handling
            back_btn = Button(
                size_hint=(None, None),
                size=(60, 45),  # Square button to match playlist_page.py appearance
                pos_hint={'x': 0.02, 'top': 0.98},  # Position similar to playlist header
                background_normal=icon_path,
                background_color=(1, 1, 1, 1),
                border=(0, 0, 0, 0)
            )
        else:
            # Fallback to text if image not found
            back_btn = Button(
                text=u"←",
                font_size='32sp',  # Same font size as playlist_page.py
                size_hint=(None, None),
                size=(60, 60),  # Square button to match playlist_page.py appearance
                pos_hint={'x': 0.02, 'top': 0.98},  # Position similar to playlist header
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=(0, 0, 0, 1)
            )
        back_btn.bind(on_release=self.goto_home)
        self.ui_container.add_widget(back_btn)

        # Previous button with icon
        prev_icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'previous_arrow.png')
        if os.path.exists(prev_icon_path):
            prev_btn = Button(
                size_hint=(None, None),
                size=(50, 40),
                pos_hint={'x': 0.03, 'center_y': 0.5},
                background_normal=prev_icon_path,
                background_color=(1, 1, 1, 1),
                border=(0, 0, 0, 0)
            )
        else:
            # Fallback to text if image not found
            prev_btn = Button(
                text='<',
                font_size='60sp',
                size_hint=(None, None),
                size=(50, 40),
                pos_hint={'x': 0.03, 'center_y': 0.5},
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=(0.2, 0.2, 0.2, 1)
            )
        prev_btn.bind(on_release=self.prev_image)
        self.ui_container.add_widget(prev_btn)

        # Next button with icon
        next_icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'next_arrow.png')
        if os.path.exists(next_icon_path):
            next_btn = Button(
                size_hint=(None, None),
                size=(50, 40),
                pos_hint={'right': 0.97, 'center_y': 0.5},
                background_normal=next_icon_path,
                background_color=(1, 1, 1, 1),
                border=(0, 0, 0, 0)
            )
        else:
            # Fallback to text if image not found
            next_btn = Button(
                text='>',
                font_size='60sp',
                size_hint=(None, None),
                size=(50, 40),
                pos_hint={'right': 0.97, 'center_y': 0.5},
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=(0.2, 0.2, 0.2, 1)
            )
        next_btn.bind(on_release=self.next_image)
        self.ui_container.add_widget(next_btn)

        layout.add_widget(self.ui_container)
        self.add_widget(layout)

        # --- UI auto-hide logic ---
        self._ui_timer = None
        # 初始化時隱藏UI
        self.hide_ui()

    def set_selected_images(self, selected_images):
        """設置選中的圖片列表"""
        self.selected_images = selected_images
        print(f"SlideshowScreen received {len(selected_images)} selected images")
        print(f"Selected images: {selected_images[:3]}...")  # 显示前3个

    def on_pre_enter(self, *args):
        """頁面進入前準備"""
        print(f"SlideshowScreen on_pre_enter - selected_images: {self.selected_images}")
        
        # 不要在这里调用refresh_images，因为它会覆盖自定义播放列表
        # self.service.refresh_images()
        
        # 如果有選中的圖片，設置為自定義播放列表
        if self.selected_images and len(self.selected_images) > 0:
            print(f"Setting custom playlist with {len(self.selected_images)} images")
            self.service.set_custom_playlist(self.selected_images)
        else:
            print("No selected images, using all images")
            # 如果沒有選中的圖片，使用所有圖片
            self.service.clear_custom_playlist()
            # 只有在没有自定义播放列表时才刷新图片
            self.service.refresh_images()
        
        # 設置圖片改變時的回調函數
        self.service.set_image_changed_callback(self.on_image_changed)
        
        # 顯示當前圖片
        current_image = self.service.get_current_image()
        print(f"Current image: {current_image}")
        if current_image:
            self.img_widget.source = current_image
        
        # 啟動自動播放
        self.service.start_auto_play()
        
        # 確保進入畫面時UI是隱藏的
        self.hide_ui()

    def on_leave(self, *args):
        """離開頁面時停止自動播放"""
        # 停止自動播放
        self.service.stop_auto_play()
        
        # 離開畫面時取消計時器
        if self._ui_timer:
            self._ui_timer.cancel()
            self._ui_timer = None

    def on_image_changed(self, image_path):
        """圖片改變時的回調函數 - 使用Clock確保在主線程中更新UI"""
        # 使用Clock.schedule_once確保UI更新在主線程中進行
        Clock.schedule_once(lambda dt: self._update_image_safe(image_path), 0)

    def _update_image_safe(self, image_path):
        """在主線程中安全地更新圖片"""
        try:
            if image_path and os.path.exists(image_path):
                self.img_widget.source = image_path
                # 強制重新加載圖片
                self.img_widget.reload()
            else:
                print(f"圖片路徑不存在或無效: {image_path}")
        except Exception as e:
            print(f"更新圖片時發生錯誤: {e}")

    def next_image(self, instance):
        # 手動切換圖片時停止自動播放
        self.service.stop_auto_play()
        next_img = self.service.next_image()
        if next_img:
            self.img_widget.source = next_img
            self.img_widget.reload()
        # 切換圖片時也重置UI計時器
        self.reset_ui_timer()

    def prev_image(self, instance):
        # 手動切換圖片時停止自動播放
        self.service.stop_auto_play()
        prev_img = self.service.prev_image()
        if prev_img:
            self.img_widget.source = prev_img
            self.img_widget.reload()
        # 切換圖片時也重置UI計時器
        self.reset_ui_timer()

    def goto_home(self, instance):
        # 返回主頁時停止自動播放
        self.service.stop_auto_play()
        self.manager.current = 'home'

    def on_touch_down(self, touch):
        # 處理觸碰事件，確保UI顯示並重置計時器
        self.show_ui()
        self.reset_ui_timer()
        # 繼續傳遞觸碰事件給子元件
        return super().on_touch_down(touch)

    def show_ui(self):
        self.ui_container.opacity = 1
        self.ui_container.disabled = False

    def hide_ui(self, *args):
        self.ui_container.opacity = 0
        self.ui_container.disabled = True

    def reset_ui_timer(self):
        if self._ui_timer:
            self._ui_timer.cancel()
        self._ui_timer = Clock.schedule_once(self.hide_ui, 5) 