import io
import base64
from PIL import Image

def pillow_to_b64(pil_image, img_format = "PNG"):
    buffered = io.BytesIO() # create a virtual buffer
    pil_image.save(buffered, format = img_format) # save the image to that virtual buffer

    img_bytes_array = buffered.getvalue() # get the data from that buffer
    base64_encoded_bytes = base64.b64encode(img_bytes_array)
    base64_encoded_string = base64_encoded_bytes.decode("utf-8")
    return base64_encoded_string