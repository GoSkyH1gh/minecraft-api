from minecraft_api import getMojangAPIData
from hypixel_api import getHypixelData
from cape_animator import capeAnimator
import flet as ft
import os
from dotenv import load_dotenv
from PIL import Image
import time
import threading
import io
import base64

# contains flet ui and calls other modules

load_dotenv()

cape_id = ""
uuid = ""
cape_showcase = None
cape_back = None

def pillow_to_b64(pil_image, img_format = "PNG"):
    buffered = io.BytesIO()
    pil_image.save(buffered, format = img_format)
    img_bytes_array = buffered.getvalue()
    base64_encoded_bytes = base64.b64encode(img_bytes_array)
    base64_encoded_string = base64_encoded_bytes.decode("utf-8")
    return base64_encoded_string    

def cape_animation_in_thread(page_obj, cape_img_control):
    animator = capeAnimator(Image.open(os.path.join(os.path.dirname(__file__), "cape", f"{cape_id}.png")))
    while animator.get_revealed_pixels() < 160:
        cape_img_control.src_base64 = animator.animate()
        page_obj.update()
        time.sleep(0.04)


def main(page: ft.Page):
    page.title = "FakeMC"

    def get_data_from_button(e):
        data_entered = username_entry.value.strip()
        update_contents(data_entered)
        
    def create_cape_showcase(file):
        cape_item = ft.Image(
                src = os.path.join(os.path.dirname(__file__), "cape", file),
                fit = ft.ImageFit.FIT_HEIGHT,
                filter_quality = ft.FilterQuality.NONE,
                height = 80,
            )
        
        cape_name = ft.Text(value = file[:-4], text_align = ft.alignment.center)
        
        cape_gallery.controls.append(
            ft.Column(controls = [cape_item, cape_name], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )
        
    def cape_hover(e):
        if e.data == "true":
            if has_cape:
                cape_showcase_img.src_base64 = pillow_to_b64(cape_back)
                page.update()
        else:
            if has_cape:
                cape_showcase_img.src_base64 = pillow_to_b64(cape_showcase)        
                page.update()
    
    def update_contents(data_entered, reload_needed = True):
        global cape_id
        global uuid
        global has_cape
        global cape_showcase
        global cape_back

        skin_showcase_img.scale = 0.3
        page.update()

        if len(data_entered) <= 16: # if text inputed is less than 16 chars (max username length) search is treated as an uuid
            user = getMojangAPIData(data_entered)
        else:
            user = getMojangAPIData(None, data_entered)
        formated_username, uuid, has_cape, skin_id, cape_id, lookup_failed, cape_showcase, cape_back = user.get_data()
        
        if lookup_failed:
            formated_username_text.value = "Lookup failed"
            uuid_text.value = ""
            skin_showcase_img.src = "None.png"
            cape_showcase_img.src = "None.png"
            cape_name.value = ""
            guild_list_view.controls.clear()
        else:
            formated_username_text.value = formated_username
            uuid_text.value = f"uuid: {uuid}"

            skin_showcase_img.src = os.path.join(os.path.dirname(__file__), "skin", f"{skin_id}.png")
            if has_cape:
                animation_thread = threading.Thread(
                    target=cape_animation_in_thread,
                    args = (
                        page,
                        cape_showcase_img
                    ),
                )
                animation_thread.daemon = True
                animation_thread.start()

                cape_name.value = cape_id
            else:
                cape_showcase_img.src_base64 = pillow_to_b64(Image.open(os.path.join(os.path.dirname(__file__), "cape", "no_cape.png")))
                cape_name.value = ""
        
        skin_showcase_img.scale = 1 # animates skin showcase img

        # --- Hypixel api integration ---
        api_key = os.getenv("hypixel_api_key")
        user1 = getHypixelData(uuid, api_key)
        first_login, player_rank = user1.get_basic_data()
        if first_login != None and player_rank != None:
            first_login_text.value = f"Account first saw on: {first_login}"
            player_rank_text.value = player_rank
            page.update()
        else:
            first_login_text.value = ""
            player_rank_text.value = ""
            page.update()
        guild_members = []
        guild_members = user1.get_guild_info()
        print(guild_members)

        if guild_members == None:
            guild_list_view.controls.clear()
            page.update()

        if reload_needed:
            guild_list_view.controls.clear()
            if guild_members is not None:
                for member in guild_members:
                    guild_showcase = getMojangAPIData(None, member)
                    guild_member_name = guild_showcase.get_name()
                    if guild_member_name is not None:
                        guild_list_view.controls.append(ft.Button(text = guild_member_name, on_click = lambda e, name_to_pass = guild_member_name: update_contents(name_to_pass, False)))
                        page.update()
    
    # --- tab 1 (home) ---
    
    username_entry = ft.TextField(border_color = "#EECCDD", on_submit = get_data_from_button, hint_text="Search by username or UUID")
    get_data_button = ft.Button(on_click = get_data_from_button, text = "Get Data")
    
    search = ft.Row(controls = [username_entry, get_data_button])
    search_c = ft.Container(padding = ft.padding.only(120, 10), content = search)

    formated_username_text = ft.Text(size=30)
    uuid_text = ft.Text(selectable = True)

    info = ft.Column(controls = [formated_username_text, uuid_text])
    info_c = ft.Container(content = info, padding = ft.padding.only(120, 10))
    
    skin_showcase_img = ft.Image(
        src="None.png", height = 200, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE, scale = 0.3, animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT)
        )
    cape_showcase_img = ft.Image(src="None.png", height = 150, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE)

    cape_showcase_img_c = ft.Container(content = cape_showcase_img, on_hover=cape_hover)

    cape_name = ft.Text(value = "")

    first_login_text = ft.Text(value = "")
    player_rank_text = ft.Text(value = "")

    hypixel_info_card = ft.Card(content=ft.Container(
        content = ft.Column(
            controls= [first_login_text, player_rank_text]
            ),
        padding = ft.padding.all(20),
        alignment=ft.alignment.top_center
        ),
        elevation = 1,
        margin = ft.padding.only(right = 60)
        
    )
    
    guild_list_view = ft.ListView(spacing = 10, width = 200, height = 450, auto_scroll = True,)
    guild_list_view_c = ft.Container(content = guild_list_view, margin = ft.margin.only(bottom = 50, right = 30))

    img_displays = ft.Row(controls = [skin_showcase_img, cape_showcase_img_c, cape_name], alignment=ft.alignment.top_center)
    img_displays_c = ft.Container(padding = ft.padding.only(150, 10), content = img_displays)

    hypixel_display = ft.Row(controls = [hypixel_info_card, guild_list_view_c], vertical_alignment=ft.CrossAxisAlignment.START)

    main_info = ft.Row(controls=[img_displays_c, hypixel_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)

    main_page = ft.Column(controls = [search_c, info_c, main_info])

    home_page = main_page

    # --- tab 2 (cape gallery) ---
    cape_gallery = ft.GridView(
        spacing = 5,
        expand = True,
        max_extent=150,
    )


    tabs = ft.Tabs(
        selected_index = 0,
        animation_duration = 300,
        tabs = [
            ft.Tab(
                text = "Home",
                content = ft.Container(
                    content = home_page
                ),
            ),
            ft.Tab(
                text = "Capes",
                content = ft.Container(
                    content = cape_gallery,
                    padding = 20
                )
            )
        ]
    )

    page.add(tabs)

    for file in os.listdir(os.path.join(os.path.dirname(__file__), "cape")):
        if "raw" not in file and "no_cape" not in file and "back" not in file:
            create_cape_showcase(file)
    page.update()

ft.app(main)

