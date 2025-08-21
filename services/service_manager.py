import os
from services.slideshow_service import SlideshowService
from repositories.image_repository import ImageRepository

class ServiceManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            # 使用隨身碟路徑（無空格）
            IMAGES_DIR = '/media/jh-pi/ESD-USB/images'
            # 如果隨身碟不存在，則使用本地路徑作為備用
            if not os.path.exists(IMAGES_DIR):
                IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')
                print(f"隨身碟路徑不存在，使用本地路徑: {IMAGES_DIR}")
            else:
                print(f"使用隨身碟路徑: {IMAGES_DIR}")
            
            self.repository = ImageRepository(IMAGES_DIR)
            
            # 在初始化時就完成圖片處理，避免後續重複處理
            print("正在初始化圖片服務...")
            self.repository.get_image_files()  # 這會觸發縮圖創建
            print("圖片服務初始化完成！")
            
            self.slideshow_service = SlideshowService(self.repository)
            self.slideshow_interval = 3.0  # 默认间隔时间
            self.slideshow_loop = True     # 默认开启循环
            self.brightness = 50           # 默认亮度
            self.initialized = True
    
    def get_slideshow_service(self):
        """获取幻灯片服务实例"""
        return self.slideshow_service
    
    def set_slideshow_interval(self, interval: float):
        """设置幻灯片间隔时间"""
        self.slideshow_interval = interval
        # 更新幻灯片服务的间隔时间
        self.slideshow_service.set_auto_play_interval(interval)
    
    def get_slideshow_interval(self) -> float:
        """获取幻灯片间隔时间"""
        return self.slideshow_interval
    
    def set_slideshow_loop(self, loop: bool):
        """设置幻灯片循环播放"""
        self.slideshow_loop = loop
        # 更新幻灯片服务的循环播放设置
        self.slideshow_service.set_slideshow_loop(loop)
    
    def get_slideshow_loop(self) -> bool:
        """获取幻灯片循环播放设置"""
        return self.slideshow_loop
    
    def set_brightness(self, brightness: int):
        """设置亮度"""
        self.brightness = brightness
    
    def get_brightness(self) -> int:
        """获取亮度设置"""
        return self.brightness
    
    def get_all_settings(self):
        """获取所有设置"""
        return {
            'slideshow_interval': self.slideshow_interval,
            'slideshow_loop': self.slideshow_loop,
            'brightness': self.brightness
        }
    
    def set_all_settings(self, settings: dict):
        """设置所有设置"""
        if 'slideshow_interval' in settings:
            self.set_slideshow_interval(settings['slideshow_interval'])
        if 'slideshow_loop' in settings:
            self.set_slideshow_loop(settings['slideshow_loop'])
        if 'brightness' in settings:
            self.set_brightness(settings['brightness'])
