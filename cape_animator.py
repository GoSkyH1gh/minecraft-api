from PIL import Image
import base64
import io

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
        return self.pillow_to_b64(self.animated_pil_image)

    def pillow_to_b64(self, pil_image, img_format = "PNG"):
        buffered = io.BytesIO()
        pil_image.save(buffered, format = img_format)
        img_bytes_array = buffered.getvalue()
        base64_encoded_bytes = base64.b64encode(img_bytes_array)
        base64_encoded_string = base64_encoded_bytes.decode("utf-8")
        return base64_encoded_string

    def get_revealed_pixels(self):
        return self.revealed_pixels


if __name__ == "__main__":
    cape_img = Image.open("C:/Users/serba/Downloads/Founder's.png")
    founders_cape = capeAnimator(cape_img)
    while founders_cape.revealed_pixels <= founders_cape.total_pixels:
        founders_cape.animate()
    founders_cape.animated_pil_image.show()
