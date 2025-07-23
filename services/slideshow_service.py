class SlideshowService:
    def __init__(self, image_repository):
        self.image_repository = image_repository
        self.images = self.image_repository.get_image_files()
        self.index = 0

    def refresh_images(self):
        self.images = self.image_repository.get_image_files()
        self.index = 0

    def get_current_image(self):
        if not self.images:
            return ''
        return self.images[self.index]

    def next_image(self):
        if not self.images:
            return ''
        self.index = (self.index + 1) % len(self.images)
        return self.get_current_image()

    def prev_image(self):
        if not self.images:
            return ''
        self.index = (self.index - 1) % len(self.images)
        return self.get_current_image() 