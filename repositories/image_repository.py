import os

class ImageRepository:
    def __init__(self, images_dir):
        self.images_dir = images_dir

    def get_image_files(self):
        if not os.path.exists(self.images_dir):
            return []
        files = [os.path.join(self.images_dir, f) for f in os.listdir(self.images_dir)
                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        files.sort()
        return files 