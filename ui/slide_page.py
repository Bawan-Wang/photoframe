import os
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from services.slideshow_service import SlideshowService
from repositories.image_repository import ImageRepository

IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')

class SlideshowScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = ImageRepository(IMAGES_DIR)
        self.service = SlideshowService(self.repository)

        layout = FloatLayout()

        self.img_widget = Image(
            allow_stretch=True,
            fit_mode='cover',
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        layout.add_widget(self.img_widget)

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
        layout.add_widget(back_btn)

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
        layout.add_widget(prev_btn)

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
        layout.add_widget(next_btn)

        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self.service.refresh_images()
        self.img_widget.source = self.service.get_current_image()

    def on_leave(self, *args):
        pass

    def next_image(self, instance):
        self.img_widget.source = self.service.next_image()

    def prev_image(self, instance):
        self.img_widget.source = self.service.prev_image()

    def goto_home(self, instance):
        self.manager.current = 'home' 