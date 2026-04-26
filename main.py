from pathlib import Path

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from ui.main_page import HomeScreen
from ui.slide_page import SlideshowScreen
from ui.playlist_page import PlaylistScreen
from ui.setup_page import SetupScreen
from services.service_manager import ServiceManager
from services import voiceassist_signal

# IPC contract with voiceassist (see voiceassist exec-plans 007 + 008).
READY_FILE = Path("/tmp/photoframe.ready")
FADE_DURATION = 0.4


class MainApp(App):
    def build(self):
        # 設定全螢幕模式
        Window.fullscreen = 'auto'  # 自動全螢幕
        # 或者使用 'auto' 讓系統決定，或使用 True 強制全螢幕

        # 隱藏游標（可選）
        Window.show_cursor = False

        # Start hidden — fade in on on_start to match bunny's fade-out.
        try:
            Window.opacity = 0.0
        except Exception:
            pass

        # 初始化服务管理器
        self.service_manager = ServiceManager()

        Window.clearcolor = (0.95, 0.95, 0.95, 1)
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(SlideshowScreen(name='slideshow'))
        sm.add_widget(PlaylistScreen(name='playlist'))
        sm.add_widget(SetupScreen(name='setup'))
        sm.current = 'slideshow'
        return sm

    def on_start(self):
        # 1) Fade in.
        try:
            Animation(opacity=1.0, duration=FADE_DURATION).start(Window)
        except Exception:
            try:
                Window.opacity = 1.0
            except Exception:
                pass

        # 2) Tell voiceassist we are alive (its open_photoframe skill polls this).
        try:
            READY_FILE.touch()
        except Exception:
            pass

        # 3) Listen for graceful-exit requests from voiceassist.
        # The poller runs on a background thread; bounce to the Kivy main
        # thread before touching Window / App.stop().
        def _on_exit_request():
            Clock.schedule_once(lambda dt: self._graceful_exit(), 0)
        voiceassist_signal.start(_on_exit_request)

    def _graceful_exit(self):
        # Animate fade-out then stop the app.
        try:
            anim = Animation(opacity=0.0, duration=FADE_DURATION)
            anim.bind(on_complete=lambda *_: self._final_stop())
            anim.start(Window)
        except Exception:
            self._final_stop()

    def _final_stop(self):
        try:
            READY_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            self.stop()
        except Exception:
            pass

    def on_stop(self):
        # Belt-and-braces cleanup if killed without going through _graceful_exit.
        try:
            READY_FILE.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == '__main__':
    MainApp().run()