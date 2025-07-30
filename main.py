from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from ui.main_page import HomeScreen
from ui.slide_page import SlideshowScreen
from ui.playlist_page import PlaylistScreen

class MainApp(App):
    def build(self):
        Window.clearcolor = (0.95, 0.95, 0.95, 1)
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(SlideshowScreen(name='slideshow'))
        sm.add_widget(PlaylistScreen(name='playlist'))
        return sm

if __name__ == '__main__':
    MainApp().run() 