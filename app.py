from minecraft_api import getMojangAPIData
from hypixel_api import getHypixelData
import flet as ft
import os
from dotenv import load_dotenv

# contains flet ui and calls other modules

load_dotenv()

cape_id = ""
uuid = ""

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
                cape_showcase_img.src = os.path.join(os.path.dirname(__file__), "cape", f"back_{cape_id}.png")
                page.update()
        else:
            if has_cape:
                cape_showcase_img.src = os.path.join(os.path.dirname(__file__), "cape", f"{cape_id}.png")        
                page.update()
    
    def update_contents(data_entered, reload_needed = True):
        global cape_id
        global uuid
        global has_cape

        skin_showcase_img.scale = 0.3
        page.update()

        if len(data_entered) <= 16: # if text inputed is less than 16 chars (max username length) search is treated as an uuid
            user = getMojangAPIData(data_entered)
        else:
            user = getMojangAPIData(None, data_entered)
        formated_username, uuid, has_cape, skin_id, cape_id, lookup_failed = user.get_data()
        
        if lookup_failed:
            formated_username_text.value = "Lookup failed"
            uuid_text.value = ""
            skin_showcase_img.src = "None.png"
            cape_showcase_img.src = "None.png"
            cape_name.value = ""
            guild_showcase_col.controls.clear()
        else:
            formated_username_text.value = formated_username
            uuid_text.value = f"uuid: {uuid}"

            skin_showcase_img.src = os.path.join(os.path.dirname(__file__), "skin", f"{skin_id}.png")
            if has_cape:
                cape_showcase_img.src = os.path.join(os.path.dirname(__file__), "cape", f"{cape_id}.png")
                cape_name.value = cape_id
            else:
                cape_showcase_img.src = os.path.join(os.path.dirname(__file__), "cape", "no_cape.png")
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
            guild_showcase_col.controls.clear()
            page.update()

        if reload_needed:
            guild_showcase_col.controls.clear()
            if guild_members is not None:
                for member in guild_members:
                    guild_showcase = getMojangAPIData(None, member)
                    guild_member_name = guild_showcase.get_name()
                    if guild_member_name is not None:
                        guild_showcase_col.controls.append(ft.Button(text = guild_member_name, on_click = lambda e, name_to_pass = guild_member_name: update_contents(name_to_pass, False)))
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
        src="None.png", height = 200, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE, scale = 0.3, animate_scale=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT)
        )
    cape_showcase_img = ft.Image(src="None.png", height = 150, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE)

    cape_showcase_img_c = ft.Container(content = cape_showcase_img, on_hover=cape_hover)

    cape_name = ft.Text(value = "")

    first_login_text = ft.Text(value = "")
    player_rank_text = ft.Text(value = "")

    hypixel_info_card = ft.Card(content=ft.Container(
        ft.Column(controls= [first_login_text, player_rank_text]),
        padding = ft.padding.all(20)
        )
    )
    
    guild_showcase_col = ft.Column(controls = [])
    guild_showcase_col_c = ft.Container(content=guild_showcase_col, padding = ft.Padding(40, 0, 60, 0))

    img_displays = ft.Row(controls = [skin_showcase_img, cape_showcase_img_c, cape_name])
    img_displays_c = ft.Container(padding = ft.padding.only(150, 10), content = img_displays)

    hypixel_display = ft.Row(controls = [hypixel_info_card, guild_showcase_col_c])

    main_info = ft.Row(controls=[img_displays_c, hypixel_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

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
