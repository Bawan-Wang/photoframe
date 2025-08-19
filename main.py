from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from ui.main_page import HomeScreen
from ui.slide_page import SlideshowScreen
from ui.playlist_page import PlaylistScreen
from ui.setup_page import SetupScreen
from services.service_manager import ServiceManager

class MainApp(App):
    def build(self):
        # 設定全螢幕模式
        Window.fullscreen = 'auto'  # 自動全螢幕
        # 或者使用 'auto' 讓系統決定，或使用 True 強制全螢幕
        
        # 隱藏游標（可選）
        Window.show_cursor = False
        
        # 初始化服务管理器
        self.service_manager = ServiceManager()
        
        Window.clearcolor = (0.95, 0.95, 0.95, 1)
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(SlideshowScreen(name='slideshow'))
        sm.add_widget(PlaylistScreen(name='playlist'))
        sm.add_widget(SetupScreen(name='setup'))
        return sm

if __name__ == '__main__':
    MainApp().run() 