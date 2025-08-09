from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.screenmanager import Screen

class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.font_size = 24
        self.bold = True
        self.background_down = ''
        self.background_disabled_normal = ''
        self.background_disabled_down = ''
        self.border = (0, 0, 0, 0)
        with self.canvas.before:
            Color(0.27, 0.6, 0.93, 1)
            self.bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[40]
            )
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='horizontal', spacing=40, padding=40)
        btn1 = RoundedButton(text='Playlist', size_hint=(1, 1))
        btn2 = RoundedButton(text='Slideshow', size_hint=(1, 1))
        btn3 = RoundedButton(text='Setup', size_hint=(1, 1))
        btn1.bind(on_release=self.goto_playlist)
        btn2.bind(on_release=self.goto_slideshow)
        btn3.bind(on_release=self.goto_setup)
        layout.add_widget(btn1)
        layout.add_widget(btn2)
        layout.add_widget(btn3)
        self.add_widget(layout)

    def goto_playlist(self, instance):
        self.manager.current = 'playlist'

    def goto_slideshow(self, instance):
        self.manager.current = 'slideshow'
        
    def goto_setup(self, instance):
        self.manager.current = 'setup'
