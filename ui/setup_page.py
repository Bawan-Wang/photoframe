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
from services.service_manager import ServiceManager

class CustomNumberInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (60, 40)
        self.text = '1'
        self.font_size = '18sp'
        self.color = (0, 0, 0, 1)  # 黑色文字
        self.multiline = False
        # 移除过于严格的input_filter，允许用户正常输入
        # self.input_filter = 'int'  # 只允許輸入整數
        
        # 設定文字對齊 - 水平置中，垂直置中
        self.halign = 'center'
        self.valign = 'middle'
        
        # 設定文本框樣式 - 白色背景，黑色邊框
        self.background_color = (1, 1, 1, 1)  # 白色背景
        self.foreground_color = (0, 0, 0, 1)  # 黑色文字
        self.cursor_color = (0, 0, 0, 1)  # 黑色游標
        
        # 綁定文字變更事件和失去焦点事件
        self.bind(text=self.on_text_change, on_text_validate=self.on_text_validate)
    
    def on_text_change(self, instance, value):
        try:
            # 觸發回調
            if hasattr(self, 'on_value_change'):
                self.on_value_change(self, value)
        except Exception as e:
            print(f"Text change callback error: {e}")
            pass
    
    def on_text_validate(self, instance=None):
        """当用户按回车键或失去焦点时进行严格验证"""
        try:
            if hasattr(self, 'on_value_change'):
                self.on_value_change(self, self.text)
        except Exception as e:
            print(f"Text validate callback error: {e}")
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
    slideshow_loop = BooleanProperty(True)  # 默认开启循环
    brightness = NumericProperty(50)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service_manager = ServiceManager()
        self.root_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        self.build_header()
        self.build_settings()
        self.add_widget(self.root_layout)
        # 初始化时加载当前设置
        self.load_current_settings()
    
    def load_current_settings(self):
        """加载当前设置"""
        settings = self.service_manager.get_all_settings()
        self.slideshow_interval = settings['slideshow_interval']
        self.slideshow_loop = settings['slideshow_loop']
        
        # 讀取系統實際亮度值並轉換為 0-100 範圍
        self.brightness = self.get_system_brightness_percent()
        
        # 更新UI显示
        if hasattr(self, 'interval_input'):
            self.interval_input.text = str(self.slideshow_interval)
        if hasattr(self, 'loop_switch'):
            self.loop_switch.active = self.slideshow_loop
        if hasattr(self, 'brightness_label'):
            self.brightness_label.text = str(self.brightness)
        if hasattr(self, 'brightness_slider'):
            self.brightness_slider.value = self.brightness
        if hasattr(self, 'loop_status_label'):
            self.loop_status_label.text = 'On' if self.slideshow_loop else 'Off'
        
        # 确保slideshow_service的设置与UI同步
        self.service_manager.set_slideshow_interval(self.slideshow_interval)
        self.service_manager.set_slideshow_loop(self.slideshow_loop)
        self.service_manager.set_brightness(self.brightness)

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
            # 如果输入为空，不进行处理
            if not value.strip():
                return
                
            interval = int(value)
            
            # 检查范围
            if 1 <= interval <= 30:
                # 有效值，更新设置
                self.slideshow_interval = interval
                # 实时更新服务管理器中的设置
                self.service_manager.set_slideshow_interval(float(interval))
                print(f"设置幻灯片间隔为: {interval} 秒")
            else:
                # 超出范围，进行智能重置
                if interval < 1:
                    corrected_value = 1
                else:
                    corrected_value = 30
                
                # 重置为有效值
                self.interval_input.text = str(corrected_value)
                self.slideshow_interval = corrected_value
                self.service_manager.set_slideshow_interval(float(corrected_value))
                print(f"输入值 {interval} 超出范围，已自动调整为: {corrected_value} 秒")
                
        except ValueError:
            # 如果输入无效（非数字），重置为当前值
            print(f"输入值 '{value}' 不是有效数字，已重置为: {self.slideshow_interval} 秒")
            self.interval_input.text = str(self.slideshow_interval)
    
    def on_loop_change(self, instance, value):
        """處理幻燈片循環變更"""
        self.slideshow_loop = value
        self.loop_status_label.text = 'On' if value else 'Off'
        # 实时更新服务管理器中的设置
        self.service_manager.set_slideshow_loop(value)
    
    def on_brightness_change(self, instance, value):
        """處理亮度變更"""
        try:
            # 確保亮度值在 0-100 範圍內
            brightness_value = max(0, min(100, int(value)))
            
            # 更新UI顯示
            self.brightness = brightness_value
            self.brightness_label.text = str(brightness_value)
            
            # 通過 sysfs 控制硬體亮度
            self.set_system_brightness(brightness_value)
            
            # 更新服務管理器中的設置
            self.service_manager.set_brightness(brightness_value)
            
            print(f"亮度已調整為: {brightness_value}%")
            
        except Exception as e:
            print(f"調整亮度時發生錯誤: {e}")
    
    def get_system_brightness_percent(self):
        """從系統讀取當前亮度值並轉換為 0-100 百分比"""
        try:
            brightness_file = '/sys/class/backlight/11-0045/brightness'
            
            if os.path.exists(brightness_file):
                with open(brightness_file, 'r') as f:
                    current_brightness = int(f.read().strip())
                
                # 將 8-31 範圍轉換為 0-100 百分比
                # 反向映射：8 -> 0%, 31 -> 100%
                if current_brightness <= 8:
                    return 0
                elif current_brightness >= 31:
                    return 100
                else:
                    percent = int(((current_brightness - 8) / (31 - 8)) * 100)
                    return percent
            else:
                print(f"警告: 亮度控制文件不存在: {brightness_file}")
                return 50  # 預設值
                
        except Exception as e:
            print(f"讀取系統亮度時發生錯誤: {e}")
            return 50  # 預設值
    
    def set_system_brightness(self, brightness_percent):
        """通過 sysfs 設置系統亮度"""
        try:
            # 將 0-100 的百分比映射到 8-31 範圍，避免螢幕太黑
            # 使用線性映射：0% -> 8, 100% -> 31
            brightness_value = int(8 + (brightness_percent / 100.0) * (31 - 8))
            
            # 使用你系統中實際存在的亮度控制文件路徑
            brightness_file = '/sys/class/backlight/11-0045/brightness'
            
            if os.path.exists(brightness_file):
                with open(brightness_file, 'w') as f:
                    f.write(str(brightness_value))
                print(f"已通過 sysfs 設置亮度: {brightness_percent}% -> {brightness_value}/31 (映射範圍: 8-31)")
            else:
                print(f"警告: 亮度控制文件不存在: {brightness_file}")
                print("請確認 Raspberry Pi 硬體配置或使用其他亮度控制方法")
                
        except PermissionError:
            print("權限不足，無法寫入亮度控制文件")
            print("請嘗試使用 sudo 運行程序或將用戶加入 video 組")
        except Exception as e:
            print(f"設置系統亮度時發生錯誤: {e}")
    
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
        
        # 同时更新服务管理器中的设置
        self.service_manager.set_all_settings(settings)
