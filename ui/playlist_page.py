import os
import json
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle
from repositories.image_repository import ImageRepository
from ui.main_page import RoundedButton

class SmallRoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.background_down = ''
        self.background_disabled_normal = ''
        self.background_disabled_down = ''
        self.border = (0, 0, 0, 0)
        with self.canvas.before:
            Color(0.27, 0.6, 0.93, 1)
            self.bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[8]
            )
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')
CHECKBOX_STATE_FILE = os.path.join(os.path.dirname(__file__), '../checkbox_state.json')

class PlaylistScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = ImageRepository(IMAGES_DIR)
        self.selected = set()
        self.all_checkbox = None
        self.image_checkboxes = []
        self.root_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        self.build_header()
        self.build_grid()
        self.add_widget(self.root_layout)

    def save_checkbox_state(self):
        """保存勾選框狀態到文件"""
        try:
            state_data = {
                'all_selected': self.all_checkbox.active if self.all_checkbox else True,
                'selected_images': list(self.selected),
                'image_states': {}
            }
            
            # 保存每個圖片勾選框的狀態
            for checkbox in self.image_checkboxes:
                if hasattr(checkbox, 'img_path'):
                    state_data['image_states'][checkbox.img_path] = checkbox.active
            
            with open(CHECKBOX_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存勾選框狀態失敗: {e}")

    def load_checkbox_state(self):
        """從文件加載勾選框狀態"""
        try:
            if not os.path.exists(CHECKBOX_STATE_FILE):
                return None
                
            with open(CHECKBOX_STATE_FILE, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                
            return state_data
        except Exception as e:
            print(f"加載勾選框狀態失敗: {e}")
            return None

    def on_pre_enter(self, *args):
        """頁面進入前初始化選中狀態"""
        # 加載保存的狀態
        saved_state = self.load_checkbox_state()
        
        if saved_state:
            # 恢復選中的圖片集合
            self.selected.clear()
            self.selected.update(saved_state.get('selected_images', []))
            
            # 恢復All勾選框狀態
            if self.all_checkbox:
                self.all_checkbox.active = saved_state.get('all_selected', True)
            
            # 恢復個別圖片勾選框狀態
            image_states = saved_state.get('image_states', {})
            for checkbox in self.image_checkboxes:
                if hasattr(checkbox, 'img_path') and checkbox.img_path in image_states:
                    checkbox.active = image_states[checkbox.img_path]
        else:
            # 如果沒有保存的狀態，使用默認值（全部選中）
            self.selected.clear()
            all_images = self.repository.get_image_files()
            self.selected.update(all_images)
            
            if self.all_checkbox:
                self.all_checkbox.active = True
            
            for checkbox in self.image_checkboxes:
                checkbox.active = True

    def on_leave(self, *args):
        """頁面離開時保存勾選框狀態"""
        self.save_checkbox_state()

    def build_header(self):
        header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, padding=[20, 10, 20, 10], spacing=40)
        
        # Back button with icon
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'back_button.png')
        if os.path.exists(icon_path):
            # Use the icon as button background for better click handling
            back_btn = Button(
                size_hint=(None, 1), 
                width=60, 
                background_normal=icon_path,
                background_color=(1, 1, 1, 1),
                border=(0, 0, 0, 0)
            )
            back_btn.bind(on_release=self.goto_home)
            header.add_widget(back_btn)
        else:
            # Fallback to text if image not found
            back_btn = Button(text=u"←", font_size='32sp', size_hint=(None, 1), width=60, background_normal='', background_color=(0,0,0,0), color=(0,0,0,1))
            back_btn.bind(on_release=self.goto_home)
            header.add_widget(back_btn)
        
        all_box = BoxLayout(orientation='horizontal', size_hint=(None, 1), width=80, spacing=2)
        self.all_checkbox = CheckBox(size_hint=(None, 1), width=30, color=(0.1, 0.2, 0.3, 1), active=True)  # 默認選中
        self.all_checkbox.bind(active=self.on_all_checkbox)
        all_box.add_widget(self.all_checkbox)
        all_box.add_widget(Label(text='All', size_hint=(None, 1), width=40, color=(0,0,0,1)))
        header.add_widget(all_box)
        
        slideshow_btn = SmallRoundedButton(text='Slideshow', size_hint=(None, 1), width=120, font_size='20sp')
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
                img = Image(source=img_path, size_hint=(0.85, 1), pos_hint={'x': 0.15, 'y': 0}, allow_stretch=True, keep_ratio=False)
            else:
                img = Label(text='No Image', size_hint=(0.85, 1), pos_hint={'x': 0.15, 'y': 0})
            float_layout.add_widget(img)
            
            # 創建勾選框並設置為選中狀態（因為All默認選中）
            checkbox = CheckBox(
                size_hint=(None, None), 
                size=(30, 30), 
                pos_hint={'x': -0.05, 'center_y': 0.80}, 
                color=(0.1, 0.2, 0.3, 1),
                active=True  # 默認選中
            )
            checkbox.bind(active=self.on_checkbox)
            checkbox.img_path = img_path  # 保存圖片路徑
            self.image_checkboxes.append(checkbox)
            float_layout.add_widget(checkbox)
            
            cell.add_widget(float_layout)
            label = Label(text=f'Image {idx+1}', size_hint=(1, None), height=30, color=(0,0,0,1))
            cell.add_widget(label)
            grid.add_widget(cell)
        
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)
        self.root_layout.add_widget(scroll)

    def on_checkbox(self, checkbox, value):
        """處理個別圖片勾選框的變化"""
        if value:
            self.selected.add(checkbox.img_path)
        else:
            self.selected.discard(checkbox.img_path)
        
        # 檢查是否需要更新All勾選框狀態
        self.update_all_checkbox_state()
        
        # 保存狀態
        self.save_checkbox_state()

    def on_all_checkbox(self, checkbox, value):
        """處理All勾選框的變化"""
        # 暫時解綁所有個別勾選框，避免觸發on_checkbox
        for cb in self.image_checkboxes:
            cb.unbind(active=self.on_checkbox)
        
        # 同步所有個別勾選框的狀態
        for cb in self.image_checkboxes:
            cb.active = value
            if value:
                self.selected.add(cb.img_path)
            else:
                self.selected.discard(cb.img_path)
        
        # 重新綁定所有個別勾選框
        for cb in self.image_checkboxes:
            cb.bind(active=self.on_checkbox)
        
        # 保存狀態
        self.save_checkbox_state()

    def update_all_checkbox_state(self):
        """根據個別勾選框狀態更新All勾選框狀態"""
        # 暫時解綁All勾選框，避免觸發on_all_checkbox
        self.all_checkbox.unbind(active=self.on_all_checkbox)
        
        # 檢查是否所有圖片都被選中
        all_selected = all(cb.active for cb in self.image_checkboxes)
        self.all_checkbox.active = all_selected
        
        # 重新綁定All勾選框
        self.all_checkbox.bind(active=self.on_all_checkbox)

    def goto_home(self, instance):
        # 保存狀態後跳轉
        self.save_checkbox_state()
        self.manager.current = 'home'

    def goto_slideshow(self, instance):
        """跳轉到幻燈片頁面並傳遞選中的圖片列表"""
        # 獲取選中的圖片列表
        selected_images = list(self.selected)
        
        # 檢查是否有選中的圖片
        if not selected_images:
            # 如果沒有選中任何圖片，顯示提示並返回
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            from kivy.uix.button import Button
            from kivy.uix.boxlayout import BoxLayout
            
            # 創建提示彈窗
            content = BoxLayout(orientation='vertical', padding=30, spacing=20)
            content.add_widget(Label(
                text='Please select at least one image to play',
                size_hint=(1, None),
                height=80, # 進一步增加高度
                halign='center',
                valign='middle'
            ))
            
            close_btn = Button(
                text='OK',
                size_hint=(None, None),
                size=(120, 45),
                pos_hint={'center_x': 0.5}
            )
            content.add_widget(close_btn)
            
            popup = Popup(
                title='Notice',
                content=content,
                size_hint=(None, None),
                size=(350, 200), # 增加彈窗高度
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                auto_dismiss=False
            )
            
            def close_popup(instance):
                popup.dismiss()
            
            close_btn.bind(on_release=close_popup)
            popup.open()
            return
        
        # 保存狀態
        self.save_checkbox_state()
        
        # 將選中的圖片列表傳遞給幻燈片頁面
        slideshow_screen = self.manager.get_screen('slideshow')
        slideshow_screen.set_selected_images(selected_images)
        
        # 跳轉到幻燈片頁面
        self.manager.current = 'slideshow' 