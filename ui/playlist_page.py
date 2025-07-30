import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from repositories.image_repository import ImageRepository

IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')

class PlaylistScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = ImageRepository(IMAGES_DIR)
        self.selected = set()
        self.root_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        self.build_header()
        self.build_grid()
        self.add_widget(self.root_layout)

    def build_header(self):
        header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, padding=[20, 10, 20, 10], spacing=40)
        back_btn = Button(text=u"\u21B6", font_size='32sp', size_hint=(None, 1), width=60, background_normal='', background_color=(0,0,0,0), color=(0,0,0,1))
        back_btn.bind(on_release=self.goto_home)
        header.add_widget(back_btn)
        all_box = BoxLayout(orientation='horizontal', size_hint=(None, 1), width=80, spacing=2)
        all_checkbox = CheckBox(size_hint=(None, 1), width=30, color=(0.1, 0.2, 0.3, 1))
        all_checkbox.bind(active=self.on_all_checkbox)
        all_box.add_widget(all_checkbox)
        all_box.add_widget(Label(text='All', size_hint=(None, 1), width=40, color=(0,0,0,1)))
        header.add_widget(all_box)
        slideshow_btn = Button(text='Slideshow', size_hint=(None, 1), width=120, background_normal='', background_color=(0.27, 0.6, 0.93, 1), color=(1,1,1,1), font_size='20sp')
        slideshow_btn.bind(on_release=self.goto_slideshow)
        header.add_widget(slideshow_btn)
        self.root_layout.add_widget(header)

    def build_grid(self):
        images = self.repository.get_image_files()
        grid = GridLayout(cols=4, spacing=20, padding=[20, 20, 20, 20], size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for idx, img_path in enumerate(images):
            cell = BoxLayout(orientation='vertical', size_hint_y=None, height=180)
            float_layout = FloatLayout(size_hint=(1, None), height=100)
            if os.path.exists(img_path):
                img = Image(source=img_path, size_hint=(1, 1), pos_hint={'x': 0, 'y': 0}, allow_stretch=True, keep_ratio=True)
            else:
                img = Label(text='No Image', size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            float_layout.add_widget(img)
            checkbox = CheckBox(size_hint=(None, None), size=(30, 30), pos_hint={'x': 0, 'top': 1}, color=(0.1, 0.2, 0.3, 1))
            checkbox.bind(active=self.on_checkbox)
            float_layout.add_widget(checkbox)
            cell.add_widget(float_layout)
            label = Label(text=f'Image {idx+1}', size_hint=(1, None), height=30, color=(0,0,0,1))
            cell.add_widget(label)
            grid.add_widget(cell)
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)
        self.root_layout.add_widget(scroll)

    def on_checkbox(self, checkbox, value):
        # Placeholder for checkbox logic
        pass

    def on_all_checkbox(self, checkbox, value):
        # Placeholder for select all logic
        pass

    def goto_home(self, instance):
        self.manager.current = 'home'

    def goto_slideshow(self, instance):
        self.manager.current = 'slideshow' 