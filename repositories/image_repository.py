import os
from PIL import Image as PILImage

class ImageRepository:
    def __init__(self, images_dir):
        self.images_dir = images_dir
        # 創建縮圖目錄
        self.thumbnails_dir = os.path.join(os.path.dirname(images_dir), 'thumbnails')
        self._ensure_thumbnails_dir()
        
        # 縮圖設定
        self.max_thumbnail_size = (800, 600)  # 最大縮圖尺寸
        self.max_file_size = 5 * 1024 * 1024  # 5MB 限制
        
        # 緩存已處理的圖片列表
        self._processed_images_cache = None
        self._is_initialized = False

    def _ensure_thumbnails_dir(self):
        """確保縮圖目錄存在"""
        if not os.path.exists(self.thumbnails_dir):
            os.makedirs(self.thumbnails_dir)
    
    def _should_create_thumbnail(self, file_path):
        """判斷是否需要創建縮圖"""
        try:
            # 檢查檔案大小
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return True
            
            # 檢查是否已有縮圖
            filename = os.path.basename(file_path)
            thumbnail_path = os.path.join(self.thumbnails_dir, filename)
            if not os.path.exists(thumbnail_path):
                return True
                
            return False
        except Exception:
            return False
    
    def _create_thumbnail(self, file_path):
        """創建縮圖"""
        try:
            # 檢查原檔案是否存在
            if not os.path.exists(file_path):
                print(f"原檔案不存在: {file_path}")
                return file_path
            
            filename = os.path.basename(file_path)
            thumbnail_path = os.path.join(self.thumbnails_dir, filename)
            
            # 使用 PIL 創建縮圖
            with PILImage.open(file_path) as img:
                # 轉換為 RGB 模式（處理 RGBA 等格式）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 計算縮圖尺寸，保持比例
                img.thumbnail(self.max_thumbnail_size, PILImage.Resampling.LANCZOS)
                
                # 保存縮圖，使用較高品質
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                
            # 驗證縮圖是否成功創建
            if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
                print(f"已成功創建縮圖: {filename}")
                return thumbnail_path
            else:
                print(f"縮圖創建失敗: {thumbnail_path}")
                return file_path
                
        except Exception as e:
            print(f"創建縮圖失敗 {file_path}: {e}")
            return file_path  # 失敗時返回原檔案路徑

    def _initialize_images(self):
        """初始化圖片列表，只執行一次"""
        if self._is_initialized:
            return self._processed_images_cache
        
        print("正在初始化圖片列表，創建必要的縮圖...")
        
        if not os.path.exists(self.images_dir):
            self._processed_images_cache = []
            self._is_initialized = True
            return self._processed_images_cache
        
        image_files = []
        for f in os.listdir(self.images_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                file_path = os.path.join(self.images_dir, f)
                
                # 檢查是否需要創建縮圖
                if self._should_create_thumbnail(file_path):
                    thumbnail_path = self._create_thumbnail(file_path)
                    image_files.append(thumbnail_path)
                else:
                    # 使用現有縮圖
                    filename = os.path.basename(file_path)
                    thumbnail_path = os.path.join(self.thumbnails_dir, filename)
                    if os.path.exists(thumbnail_path):
                        image_files.append(thumbnail_path)
                    else:
                        image_files.append(file_path)
        
        image_files.sort()
        self._processed_images_cache = image_files
        self._is_initialized = True
        
        print(f"圖片初始化完成，共 {len(image_files)} 張圖片")
        return image_files

    def get_image_files(self):
        """獲取圖片檔案列表，使用緩存避免重複處理"""
        if self._processed_images_cache is None:
            return self._initialize_images()
        return self._processed_images_cache
    
    def refresh_images(self):
        """強制刷新圖片列表（清除緩存並重新處理）"""
        print("強制刷新圖片列表...")
        self._processed_images_cache = None
        self._is_initialized = False
        return self._initialize_images()
    
    def clear_cache(self):
        """清除緩存"""
        self._processed_images_cache = None
        self._is_initialized = False
        print("圖片緩存已清除")
    
    def get_original_image_path(self, thumbnail_path):
        """根據縮圖路徑獲取原圖路徑"""
        filename = os.path.basename(thumbnail_path)
        original_path = os.path.join(self.images_dir, filename)
        if os.path.exists(original_path):
            return original_path
        return thumbnail_path 