import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import NumericProperty, BooleanProperty

class CustomNumberInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (60, 40)
        self.text = '1'
        self.font_size = '18sp'
        self.color = (0, 0, 0, 1)  # 黑色文字
        self.multiline = False
        self.input_filter = 'int'  # 只允許輸入整數
        
        # 設定文字對齊 - 水平置中，垂直置中
        self.halign = 'center'
        self.valign = 'middle'
        
        # 設定文本框樣式 - 白色背景，黑色邊框
        self.background_color = (1, 1, 1, 1)  # 白色背景
        self.foreground_color = (0, 0, 0, 1)  # 黑色文字
        self.cursor_color = (0, 0, 0, 1)  # 黑色游標
        
        # 綁定文字變更事件
        self.bind(text=self.on_text_change)
    
    def on_text_change(self, instance, value):
        try:
            # 觸發回調
            if hasattr(self, 'on_value_change'):
                self.on_value_change(self, value)
        except:
            pass

class RoundedSwitch(Switch):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.27, 0.6, 0.93, 1)  # 深藍色
        self.active = False

class RoundedSlider(Slider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.min = 0
        self.max = 100
        self.value = 50
        self.step = 1
        self.background_width = 4
        self.background_color = (0.27, 0.6, 0.93, 1)  # 深藍色
        self.background_disabled_color = (0.27, 0.6, 0.93, 1)
        self.cursor_size = (20, 20)
        self.cursor_disabled = False

class SetupScreen(Screen):
    slideshow_interval = NumericProperty(1)
    slideshow_loop = BooleanProperty(False)
    brightness = NumericProperty(50)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        self.build_header()
        self.build_settings()
        self.add_widget(self.root_layout)
    
    def build_header(self):
        """構建頁面標題和返回按鈕"""
        header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, padding=[20, 10, 20, 10])
        
        # 返回按鈕
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'back_button.png')
        if os.path.exists(icon_path):
            back_btn = Button(
                size_hint=(None, 1), 
                width=60, 
                background_normal=icon_path,
                background_color=(1, 1, 1, 1),
                border=(0, 0, 0, 0)
            )
        else:
            back_btn = Button(
                text=u"←", 
                font_size='32sp', 
                size_hint=(None, 1), 
                width=60, 
                background_normal='', 
                background_color=(0,0,0,0), 
                color=(0,0,0,1)
            )
        
        back_btn.bind(on_release=self.goto_home)
        header.add_widget(back_btn)
        
        # 標題
        title = Label(
            text='Settings', 
            size_hint=(1, 1), 
            color=(0, 0, 0, 1),
            font_size='24sp',
            halign='center',
            valign='middle'
        )
        header.add_widget(title)
        
        # 右側空白佔位
        header.add_widget(Label(size_hint=(None, 1), width=60))
        
        self.root_layout.add_widget(header)
    
    def build_settings(self):
        """構建設定選項"""
        # 創建一個水平置中的容器
        center_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 1)
        )
        
        # 左側空白
        center_container.add_widget(Label(size_hint=(0.15, 1)))
        
        # 設定選項容器
        settings_container = BoxLayout(
            orientation='vertical', 
            spacing=60, 
            padding=[20, 0, 20, 0],
            size_hint=(0.7, 1)
        )
        
        # 上方空白 - 讓設定選項分布在中央
        settings_container.add_widget(Label(size_hint=(1, 0.25)))
        
        # 幻燈片間隔設定
        interval_layout = self.build_interval_setting()
        settings_container.add_widget(interval_layout)
        
        # 幻燈片循環設定
        loop_layout = self.build_loop_setting()
        settings_container.add_widget(loop_layout)
        
        # 亮度設定
        brightness_layout = self.build_brightness_setting()
        settings_container.add_widget(brightness_layout)
        
        # 下方空白 - 讓設定選項分布在中央
        settings_container.add_widget(Label(size_hint=(1, 0.25)))
        
        center_container.add_widget(settings_container)
        
        # 右側空白
        center_container.add_widget(Label(size_hint=(0.15, 1)))
        
        self.root_layout.add_widget(center_container)
    
    def build_interval_setting(self):
        """構建幻燈片間隔設定"""
        layout = BoxLayout(orientation='horizontal', size_hint=(0.8, None), height=50, spacing=100)
        
        # 標籤
        label = Label(
            text='Slideshow Interval',
            size_hint=(1, 1),
            color=(0, 0, 0, 1),
            font_size='18sp',
            halign='left',
            valign='middle'
        )
        layout.add_widget(label)
        
        # 數值輸入框
        self.interval_input = CustomNumberInput()
        self.interval_input.text = str(self.slideshow_interval)
        self.interval_input.on_value_change = self.on_interval_change
        layout.add_widget(self.interval_input)
        
        # 單位說明
        unit_label = Label(
            text='Sec. (Max. 30 Sec.)',
            size_hint=(0.001, 1),
            color=(0.5, 0.5, 0.5, 1),
            font_size='14sp',
            halign='left',
            valign='middle'
        )
        layout.add_widget(unit_label)
        
        return layout
    
    def build_loop_setting(self):
        """構建幻燈片循環設定"""
        layout = BoxLayout(orientation='horizontal', size_hint=(0.8, None), height=50, spacing=100)
        
        # 標籤
        label = Label(
            text='Slideshow Loop',
            size_hint=(1, 1),
            color=(0, 0, 0, 1),
            font_size='18sp',
            halign='left',
            valign='middle'
        )
        layout.add_widget(label)
        
        # 開關
        self.loop_switch = RoundedSwitch(
            size_hint=(None, None),
            size=(80, 40)
        )
        self.loop_switch.bind(active=self.on_loop_change)
        layout.add_widget(self.loop_switch)
        
        # 開關狀態標籤
        self.loop_status_label = Label(
            text='Off',
            size_hint=(0.001, 1),
            color=(0, 0, 0, 1),
            font_size='16sp',
            halign='center',
            valign='middle'
        )
        layout.add_widget(self.loop_status_label)
        
        return layout
    
    def build_brightness_setting(self):
        """構建亮度設定"""
        layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, spacing=10)
        
        # 標籤
        label = Label(
            text='Brightness',
            size_hint=(0.2, 1),
            color=(0, 0, 0, 1),
            font_size='18sp',
            halign='left',
            valign='middle'
        )
        layout.add_widget(label)
        
        # 數值顯示
        self.brightness_label = Label(
            text=str(self.brightness),
            size_hint=(None, None),
            size=(60, 40),
            color=(0, 0, 0, 1),
            font_size='18sp',
            halign='center',
            valign='middle'
        )
        layout.add_widget(self.brightness_label)
        
        # 滑塊
        self.brightness_slider = RoundedSlider(
            size_hint=(0.8, None),
            height=40
        )
        self.brightness_slider.bind(value=self.on_brightness_change)
        layout.add_widget(self.brightness_slider)
        
        return layout
    
    def on_interval_change(self, instance, value):
        """處理幻燈片間隔變更"""
        try:
            interval = int(value)
            if 1 <= interval <= 30:
                self.slideshow_interval = interval
            else:
                # 如果超出範圍，重置為有效值
                if interval < 1:
                    self.interval_input.text = '1'
                else:
                    self.interval_input.text = '30'
        except ValueError:
            # 如果輸入無效，重置為當前值
            self.interval_input.text = str(self.slideshow_interval)
    
    def on_loop_change(self, instance, value):
        """處理幻燈片循環變更"""
        self.slideshow_loop = value
        self.loop_status_label.text = 'On' if value else 'Off'
    
    def on_brightness_change(self, instance, value):
        """處理亮度變更"""
        self.brightness = int(value)
        self.brightness_label.text = str(self.brightness)
    
    def goto_home(self, instance):
        """返回主頁"""
        self.manager.current = 'home'
    
    def get_settings(self):
        """獲取當前設定"""
        return {
            'slideshow_interval': self.slideshow_interval,
            'slideshow_loop': self.slideshow_loop,
            'brightness': self.brightness
        }
    
    def set_settings(self, settings):
        """設定值"""
        self.slideshow_interval = settings.get('slideshow_interval', 1)
        self.slideshow_loop = settings.get('slideshow_loop', False)
        self.brightness = settings.get('brightness', 50)
        
        # 更新UI
        self.interval_input.text = str(self.slideshow_interval)
        self.loop_switch.active = self.slideshow_loop
        self.brightness_slider.value = self.brightness
        self.brightness_label.text = str(self.brightness)
