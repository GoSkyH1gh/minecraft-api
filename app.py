from minecraft_api import getMojangAPIData
from hypixel_api import getHypixelData
from cape_animator import capeAnimator
from utils import pillow_to_b64
import flet as ft
import os
from dotenv import load_dotenv
from PIL import Image
import time
import threading
import json

# contains flet ui and calls other modules

load_dotenv()

cape_id = ""
uuid = ""
cape_showcase = None
cape_back = None
favorites_location = os.path.join(os.path.dirname(__file__), "favorites.json")

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
                cape_showcase_img.update()
        else:
            if has_cape:
                cape_showcase_img.src_base64 = pillow_to_b64(cape_showcase)        
                cape_showcase_img.update()

    def update_contents(data_entered, reload_needed = True):
        global cape_id
        global uuid
        global has_cape
        global cape_showcase
        global cape_back
        global formated_username
        
        tabs.selected_index = 0

        print(data_entered)

        skin_showcase_img.scale = 0.3
        page.update()

        if len(data_entered) <= 16: # if text inputed is less than 16 chars (max username length) search is treated as an name
            user = getMojangAPIData(data_entered)
        else:
            user = getMojangAPIData(None, data_entered)
        formated_username, uuid, has_cape, skin_id, cape_id, lookup_failed, cape_showcase, cape_back = user.get_data()
        
        if lookup_failed: # if lookup fails resets all controls
            reset_controls()
        else: # this happens if lookup is succesful
            skin_showcase_img.scale = 1 # animates skin showcase img
            page.update()
            
            formated_username_text.value = formated_username
            uuid_text.value = f"uuid: {uuid}"

            # loads skin, handles cape animation and gradient color
            skin_showcase_img.src = os.path.join(os.path.dirname(__file__), "skin", f"{skin_id}.png")
            if has_cape:
                animate_cape()
                update_gradient()

                cape_name.value = cape_id
            else:
                cape_showcase_img.src_base64 = pillow_to_b64(Image.open(os.path.join(os.path.dirname(__file__), "cape", "no_cape.png")))
                cape_name.value = ""
                home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])
                page.update()

        # checks if user is in favorites
        favorites = load_favorites()
        if not lookup_failed:
            favorite_chip.visible = True
            if {"name": formated_username, "uuid": uuid} in favorites:
                favorite_chip.icon = ft.Icons.FAVORITE_SHARP
                favorite_chip.tooltip = "Unfavorite"
            else:
                favorite_chip.icon = ft.Icons.FAVORITE_OUTLINE
                favorite_chip.tooltip = "Favorite"
        else:
            favorite_chip.visible = False
        page.update()

        load_hypixel_data(reload_needed)

    def animate_cape():
        animation_thread = threading.Thread(
            target = cape_animation_in_thread,
                args = (
                    page,
                    cape_showcase_img
            ),
        )
        animation_thread.daemon = True
        animation_thread.start()

    def reset_controls():
        formated_username_text.value = "Lookup failed"
        uuid_text.value = ""
        skin_showcase_img.src = "None.png"
        cape_showcase_img.src_base64 = ""
        cape_name.value = ""
        guild_list_view.controls.clear()
        hypixel_info_card.visible = False
        home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])

    def update_gradient():
        bgcolor_instance = capeAnimator(cape_showcase)
        bgcolor = bgcolor_instance.get_average_color_pil()
        if bgcolor is not None:
            home_page_container.gradient = ft.RadialGradient(colors = [bgcolor, ft.Colors.TRANSPARENT], center = ft.Alignment(-0.35, 0), radius = 0.7) # handle gradient color
            print(bgcolor)
        else:
            home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])
            print("no cape color found")
        page.update()

    def load_hypixel_data(reload_needed):
        # --- Hypixel api integration ---
        if uuid is not None:
            api_key = os.getenv("hypixel_api_key")
            user1 = getHypixelData(uuid, api_key)
            first_login, player_rank = user1.get_basic_data()
            if first_login != None and player_rank != None:
                hypixel_info_card.visible = True
                first_login_text.value = f"Account first saw on: {first_login}"
                player_rank_text.value = player_rank
                page.update()
            else:
                first_login_text.value = ""
                player_rank_text.value = ""
                hypixel_info_card.visible = False
                page.update()
            guild_members = []
            guild_members = user1.get_guild_info()
            print(guild_members)
        else:
            guild_list_view.controls.clear()
            page.update()
            return

        if guild_members is None:
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

    def favorites_clicked(e):
        # get data from favorites.json
        favorites = load_favorites()

        new_favorite = {"name": formated_username, "uuid": uuid}

        if new_favorite not in favorites:
            favorites.append(new_favorite)
            print(f"you added {formated_username} to favorites!\nuuid: {uuid}")
            favorite_chip.icon = ft.Icons.FAVORITE_SHARP
            favorite_chip.tooltip = "Unfavorite"
            favorite_chip.update()
        else:
            favorites.remove(new_favorite)
            print(f"you removed {formated_username} from favorites")
            favorite_chip.icon = ft.Icons.FAVORITE_OUTLINE
            favorite_chip.tooltip = "Favorite"
            favorite_chip.update()

        
        # write new favorites.json
        try:
            with open(favorites_location, "w", encoding = "utf-8") as file:
                json.dump(favorites, file, indent = 4)
        except Exception as e:
            print(f"Something went wrong while saving favorites: {e}")
        load_favorites_page()
    
    def load_favorites():
        try:
            with open(favorites_location, "r", encoding = "utf-8") as file:
                return json.load(file)
            
        except Exception as e:
            print(f"Something went while reading favorites.json: {e}")
            return []
    
    def load_favorites_page():
        favorites_listview.controls.clear()
        favorites = load_favorites()
        for favorite in favorites:
            favorites_listview.controls.append(
                ft.Button(text = favorite["name"], on_click = lambda e, uuid = favorite["uuid"]: update_contents(uuid)) # lambda so that function doesnt run on load
            )
        tabs.update()
    # --- tab 1 (home) ---
    
    
    username_entry = ft.TextField(border_color = "#EECCDD", on_submit = get_data_from_button, hint_text="Search by username or UUID")
    get_data_button = ft.Button(on_click = get_data_from_button, text = "Search")
    
    search = ft.Row(controls = [username_entry, get_data_button])
    search_c = ft.Container(padding = ft.padding.only(120, 10), content = search)

    formated_username_text = ft.Text(size=30)
    uuid_text = ft.Text(selectable = True)

    favorite_chip = ft.IconButton(
        icon = ft.Icons.FAVORITE_BORDER_OUTLINED,
        icon_color = ft.Colors.RED_400,
        on_click = favorites_clicked,
        tooltip = "Favorite",
        visible = False
    )

    favorite_chip_c = ft.Container(content = favorite_chip, padding = ft.padding.only(top = 5))

    username_row = ft.Row(controls = [formated_username_text, favorite_chip_c])

    info = ft.Column(controls = [username_row, uuid_text])
    info_c = ft.Container(content = info, padding = ft.padding.only(120, 10))
    
    skin_showcase_img = ft.Image(
        src="None.png", height = 200, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE, scale = 0.3, animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT)
        )
    
    cape_showcase_img = ft.Image(src="None.png", height = 150, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE)

    cape_showcase_img_c = ft.Container(content = cape_showcase_img, on_hover=cape_hover)

    #cape_gradient_stack = ft.Stack(controls=[home_page_container, cape_showcase_img_c])

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
        margin = ft.padding.only(right = 60),
        visible = False
        
    ) 

    guild_list_view = ft.ListView(spacing = 10, width = 200, height = 450, auto_scroll = True,)
    guild_list_view_c = ft.Container(content = guild_list_view, margin = ft.margin.only(bottom = 50, right = 30))

    img_displays = ft.Row(controls = [skin_showcase_img, cape_showcase_img_c, cape_name], alignment=ft.alignment.top_center)
    img_displays_c = ft.Container(padding = ft.padding.only(150, 10), content = img_displays)

    hypixel_display = ft.Row(controls = [hypixel_info_card, guild_list_view_c], vertical_alignment=ft.CrossAxisAlignment.START)

    main_info = ft.Row(controls=[img_displays_c, hypixel_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)

    home_page = ft.Column(controls = [search_c, info_c, main_info])

    # --- tab 2 (favorites) ---
    favorites_listview = ft.ListView(spacing = 20)

    favorites_tab = ft.Container(content = favorites_listview, margin = 20, padding = 20)


    # --- tab 3 (cape gallery) ---
    cape_gallery = ft.GridView(
        spacing = 5,
        expand = True,
        max_extent=150,
    )

    home_page_container = ft.Container(
        gradient = ft.RadialGradient(
            colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT],
        ),
        expand = True,
        visible = True,
        content = home_page
    )


    tabs = ft.Tabs(
        selected_index = 0,
        animation_duration = 300,
        tabs = [
            ft.Tab(
                text = "Home",
                content = home_page_container,
            ),
            ft.Tab(
                text = "Favorites",
                content = favorites_tab
            ),
            ft.Tab(
                text = "Capes",
                content = ft.Container(
                    content = cape_gallery,
                    padding = 20,
                )
            )
        ],
        expand = True,
    )

    page.add(tabs)

    

    for file in os.listdir(os.path.join(os.path.dirname(__file__), "cape")):
        if "raw" not in file and "no_cape" not in file and "back" not in file:
            create_cape_showcase(file)
    page.update()

    load_favorites_page()

ft.app(main)

