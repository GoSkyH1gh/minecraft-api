from utils import pillow_to_b64
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)

class capeAnimator:
    def __init__(self, cape_img):
        self.cape_img = cape_img
        self.revealed_pixels = 0
        self.total_pixels = 160
        self.animated_pil_image = Image.new("RGBA", (10, 16))
        self.current_line = 0
        self.animation_finished = False

    def animate(self):
        self.revealed_pixels += 10
        crop_area = (0, self.current_line, 10, self.current_line + 1)
        pixel_region = self.cape_img.crop(crop_area)
        self.animated_pil_image.paste(pixel_region, crop_area)
        self.current_line += 1
        return pillow_to_b64(self.animated_pil_image)

    def get_revealed_pixels(self):
        return self.revealed_pixels

    def get_average_color_pil(self):
        image = self.cape_img
        pixels = np.array(image)
        average_color = pixels.mean(axis = (0, 1))
        average_color_tuple = tuple(average_color.astype(int))

        try:
            r = int(average_color_tuple[0])
            g = int(average_color_tuple[1])
            b = int(average_color_tuple[2])
            rgb = f"#{r:02x}{g:02x}{b:02x}"
            logging.info(f"average color of cape: {rgb}")
            return rgb
        except Exception as e:
            logging.error(f"something went wrong while getting color values: {e}")
            return None


if __name__ == "__main__":
    cape_img = Image.open("C:/Users/serba/Downloads/Founder's.png")
    founders_cape = capeAnimator(cape_img)
    while founders_cape.revealed_pixels <= founders_cape.total_pixels:
        founders_cape.animate()
    founders_cape.animated_pil_image.show()
    founders_cape.get_average_color_pil()
