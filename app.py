from flet.core.alignment import center

from minecraft_api import GetMojangAPIData
from hypixel_api import GetHypixelData
from cape_animator import CapeAnimator
from utils import pillow_to_b64
import flet as ft
import os
from dotenv import load_dotenv
from PIL import Image
import time
import threading
import json
from pathlib import Path
import logging

current_file_path = Path(__file__)
current_directory = current_file_path.parent

app_logger = logging.getLogger(__name__)

logging.basicConfig(
    level = logging.INFO,
    handlers = [
        logging.StreamHandler(), # log to terminal
        logging.FileHandler(current_directory / "latest.log") # save log to latest.log
    ]
    )

# contains flet ui and calls other modules

load_dotenv()

app_logger.info(f"running in: {current_file_path}")


class FakeMCApp:
    def __init__(self, page = ft.Page):
        self.guild_name = None
        self.page = page
        self.page.title = "FakeMC"

        self.hypixel_api_key = os.getenv("hypixel_api_key")

        self.cape_id = ""
        self.uuid = ""
        self.formated_username = None
        self.lookup_failed = None
        self.cape_showcase = None
        self.cape_back = None
        self.has_cape = None
        self.skin_id = None
        self.favorites_location = current_directory / "favorites.json"
        self.api_edit_mode = False # for config tab, changes api_key to be editable
        
        self.enable_gradient = True
        self.hypixel_integration_enabled = True # enables or disables Hypixel integration
        
        self.user_dismissed_no_api_banner = False # once this is True, banner will no longer be shown

        if self.page.platform_brightness == ft.Brightness.LIGHT: # disables gradient if theme is light
            self.enable_gradient = False
            self.app_theme_light = True
        else:
            self.app_theme_light = False
        


        # flet ui starts here
        self.username_entry = ft.TextField(border_color = "#EECCDD", on_submit = self.get_data_from_button, hint_text="Search by username or UUID")
        self.get_data_button = ft.Button(on_click = self.get_data_from_button, text = "Search")
        
        self.search = ft.Row(controls = [self.username_entry, self.get_data_button])
        self.search_c = ft.Container(padding = ft.padding.only(120, 10), content = self.search)

        self.formated_username_text = ft.Text(size=30)
        self.uuid_text = ft.Text(selectable = True)

        self.favorite_chip = ft.IconButton(
            icon = ft.Icons.FAVORITE_BORDER_OUTLINED,
            icon_color = ft.Colors.RED_400,
            on_click = self.favorites_clicked,
            tooltip = "Favorite",
            visible = False
        )

        self.favorite_chip_c = ft.Container(content = self.favorite_chip, padding = ft.padding.only(top = 5))

        self.username_row = ft.Row(controls = [self.formated_username_text, self.favorite_chip_c])

        self.info = ft.Column(controls = [self.username_row, self.uuid_text])
        self.info_c = ft.Container(content = self.info, padding = ft.padding.only(120, 10))
        
        self.skin_showcase_img = ft.Image(
            src="None.png", height = 200, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE, scale = 0.3, animate_scale=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT)
            )
        
        self.cape_showcase_img = ft.Image(src="None.png", height = 150, fit = ft.ImageFit.FILL, filter_quality = ft.FilterQuality.NONE)

        self.cape_showcase_img_c = ft.Container(content = self.cape_showcase_img, on_hover = self.cape_hover)

        self.cape_name = ft.Text(value = "")

        self.first_login_text = ft.Text(value = "")
        self.player_rank_text = ft.Text(value = "")

        self.hypixel_info_card = ft.Card(content=ft.Container(
            content = ft.Column(
                controls= [self.first_login_text, self.player_rank_text]
                ),
            padding = ft.padding.all(20),
            alignment=ft.alignment.top_center
            ),
            elevation = 1,
            margin = ft.padding.only(right = 60),
            visible = False
        ) 

        self.guild_name_text = ft.Text(value = "", text_align = ft.TextAlign.CENTER)
        self.guild_list_view = ft.ListView(spacing = 10, width = 200, height = 450, auto_scroll = True)
        self.guild_col = ft.Column(controls = [self.guild_name_text, self.guild_list_view], horizontal_alignment = ft.CrossAxisAlignment.CENTER)
        self.guild_list_c = ft.Container(content = self.guild_col, margin = ft.margin.only(bottom = 50, right = 30))

        self.img_displays = ft.Row(controls = [self.skin_showcase_img, self.cape_showcase_img_c, self.cape_name], alignment=ft.alignment.top_center)
        self.img_displays_c = ft.Container(padding = ft.padding.only(150, 10), content = self.img_displays)

        self.hypixel_display = ft.Row(controls = [self.hypixel_info_card, self.guild_list_c], vertical_alignment=ft.CrossAxisAlignment.START)

        self.main_info = ft.Row(controls=[self.img_displays_c, self.hypixel_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)

        self.home_page = ft.Column(controls = [self.search_c, self.info_c, self.main_info])

        # --- tab 2 (favorites) ---
        self.favorites_listview = ft.ListView(spacing = 20)

        self.favorites_tab = ft.Container(content = self.favorites_listview, margin = 20, padding = 20)

        # --- tab 3 (cape gallery) ---
        self.cape_gallery = ft.GridView(
            spacing = 5,
            expand = True,
            max_extent=150,
        )

        # --- tab 4 (config)
        self.app_theme_dark_switch = ft.Switch(label = " Dark Theme", on_change = self.switch_theme, value = not self.app_theme_light)

        self.settings_divider = ft.Divider()

        self.enable_hypixel = ft.Switch(label = " Hypixel API integration", on_change = self.hypixel_api_switch, value = True)

        self.api_key_label = ft.Text("Current Hypixel API Key: ") # a label
        self.api_key_display = ft.Text(self.hypixel_api_key, selectable = True, font_family = "") # displays the actual key
        self.api_key_entry = ft.TextField(hint_text = "Hypixel API Key")
        self.api_key_button = ft.Button(text = "Change API Key", on_click = self.api_button_click)

        self.api_key_row = ft.Row(controls = [self.api_key_label, self.api_key_display, self.api_key_button])

        self.config_col = ft.Column(controls = [self.app_theme_dark_switch, self.settings_divider, self.enable_hypixel, self.api_key_row])

        # no api key banner

        self.no_api_key_banner = ft.Banner(
            content = ft.Text(value = "You didn't enter a Hypixel API Key. Hypixel integration requires an API Key"),
            actions = [
                ft.TextButton(text = "Ignore", on_click = self.dismiss_no_api_key_banner)
            ]
        )

        # logic for gradient
        self.home_page_container = ft.Container(
            gradient = ft.RadialGradient(
                colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT],
            ),
            expand = True,
            visible = True,
            content = self.home_page
        )

        # logic for tabs
        self.tabs = ft.Tabs(
            selected_index = 0,
            animation_duration = 300,
            tabs = [
                ft.Tab(
                    text = "Home",
                    content = self.home_page_container,
                ),
                ft.Tab(
                    text = "Favorites",
                    content = self.favorites_tab
                ),
                ft.Tab(
                    text = "Capes",
                    content = ft.Container(
                        content = self.cape_gallery,
                        padding = 20,
                    )
                ),
                ft.Tab(
                    text = "Settings",
                    content = ft.Container(
                        content = self.config_col,
                        padding = ft.padding.only(40, 20, 40, 20),
                    )
                )
            ],
            expand = True,
        )

        self.page.add(self.tabs)

    def get_data_from_button(self, e) -> None:
        data_entered = self.username_entry.value.strip()
        self.update_contents(data_entered)

    def create_cape_showcase(self, file) -> None:
        cape_item = ft.Image(
                src = current_directory / "cape" / file,
                fit = ft.ImageFit.FIT_HEIGHT,
                filter_quality = ft.FilterQuality.NONE,
                height = 80,
            )
        
        cape_name = ft.Text(value = file[:-4], text_align = ft.alignment.center)
        
        self.cape_gallery.controls.append(
            ft.Column(controls = [cape_item, cape_name], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def cape_hover(self, e) -> None:
        if e.data == "true":
            if self.has_cape:
                self.cape_showcase_img.src_base64 = pillow_to_b64(self.cape_back)
                self.cape_showcase_img.update()
        else:
            if self.has_cape:
                self.cape_showcase_img.src_base64 = pillow_to_b64(self.cape_showcase)        
                self.cape_showcase_img.update()

    def update_contents(self, data_entered, reload_needed = True) -> None:
        """
        handles updating the ui, including managing animations
        req data_entered (minecraft username or uuid)
        reload_needed should be false if hypixel guild info does not require updating
        """
        
        self.tabs.selected_index = 0

        app_logger.info(f"data entered: {data_entered}")

        self.skin_showcase_img.scale = 0.3
        self.page.update()

        if len(data_entered) <= 16: # if text inputted is less than 16 chars (max username length) search is treated as a name
            user = GetMojangAPIData(data_entered)
        else:
            user = GetMojangAPIData(None, data_entered)
        self.formated_username, self.uuid, self.has_cape, self.skin_id, self.cape_id, self.lookup_failed, self.cape_showcase, self.cape_back = user.get_data()
        
        if self.lookup_failed: # if lookup fails resets all controls
            self.reset_controls()
        else: # this happens if lookup is successful
            self.skin_showcase_img.scale = 1 # animates skin showcase img
            self.page.update()
            
            self.formated_username_text.value = self.formated_username
            self.uuid_text.value = f"uuid: {self.uuid}"

            # loads skin, handles cape animation and gradient color
            self.skin_showcase_img.src = current_directory / "skin" / f"{self.skin_id}.png"
            if self.has_cape:
                self.animate_cape()
                self.update_gradient()

                self.cape_name.value = self.cape_id
            else:
                self.cape_showcase_img.src_base64 = pillow_to_b64(Image.open(current_directory / "cape" / "no_cape.png"))
                self.cape_name.value = ""
                self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])
                self.page.update()

        # checks if user is in favorites
        favorites = self.load_favorites()
        if not self.lookup_failed:
            self.favorite_chip.visible = True
            if {"name": self.formated_username, "uuid": self.uuid, "skin_id": self.skin_id} in favorites:
                self.favorite_chip.icon = ft.Icons.FAVORITE_SHARP
                self.favorite_chip.tooltip = "Unfavorite"
            else:
                self.favorite_chip.icon = ft.Icons.FAVORITE_OUTLINE
                self.favorite_chip.tooltip = "Favorite"
        else:
            self.favorite_chip.visible = False
        self.page.update()

        if self.hypixel_api_key is not None and self.hypixel_api_key != "":
            if self.hypixel_integration_enabled:
                app_logger.info(f"accessing hypixel api with api key: {self.hypixel_api_key}")
                self.load_hypixel_data(reload_needed) 
            else:
                app_logger.info("hypixel integration is currently disabled")
        else:
            if not self.user_dismissed_no_api_banner: # only shows banner if it hasn't already been dismissed by the user
                self.page.open(self.no_api_key_banner)

    def animate_cape(self) -> None:
        animation_thread = threading.Thread(
            target = self.cape_animation_in_thread,
                args = (
                    self.page,
                    self.cape_showcase_img
            ),
        )
        animation_thread.daemon = True
        animation_thread.start()

    def reset_controls(self) -> None:
        self.formated_username_text.value = "Lookup failed"
        self.uuid_text.value = ""
        self.skin_showcase_img.src = "None.png"
        self.cape_showcase_img.src_base64 = ""
        self.cape_name.value = ""
        self.guild_list_view.controls.clear()
        self.hypixel_info_card.visible = False
        self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])

    def update_gradient(self) -> None:
        bgcolor_instance = CapeAnimator(self.cape_showcase)
        bgcolor = bgcolor_instance.get_average_color_pil()
        if bgcolor is not None and self.enable_gradient:
            self.home_page_container.gradient = ft.RadialGradient(colors = [bgcolor, ft.Colors.TRANSPARENT], center = ft.Alignment(-0.35, 0), radius = 0.7) # handle gradient color
        else:
            self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])
            app_logger.warning("Cape color not found")
        self.page.update()

    def load_hypixel_data(self, reload_needed) -> None:
        # --- Hypixel api integration ---
        if self.uuid is not None:
            user1 = GetHypixelData(self.uuid, self.hypixel_api_key)
            first_login, player_rank = user1.get_basic_data()
            if first_login is not None and player_rank is not None:
                self.hypixel_info_card.visible = True
                self.first_login_text.value = f"Account first saw on: {first_login}"
                self.player_rank_text.value = player_rank
                self.page.update()
            else:
                self.first_login_text.value = ""
                self.player_rank_text.value = ""
                self.hypixel_info_card.visible = False
                self.page.update()
            guild_members = []
            guild_members, self.guild_name = user1.get_guild_info()
            app_logger.debug(guild_members)
            app_logger.info(f"{self.formated_username}'s guild is {self.guild_name}")
        else:
            self.guild_list_view.controls.clear()
            self.page.update()
            return

        if guild_members is None:
            self.guild_list_view.controls.clear()
            self.page.update()
            self.guild_name_text.value = ""

        if reload_needed:
            self.guild_list_view.controls.clear()
            if guild_members is not None:
                for member in guild_members:
                    guild_showcase = GetMojangAPIData(None, member)
                    guild_member_name = guild_showcase.get_name()
                    if guild_member_name is not None:
                        self.guild_list_view.controls.append(ft.Button(text = guild_member_name, on_click = lambda e, name_to_pass = guild_member_name: self.update_contents(name_to_pass, False)))
                        self.page.update()
                        self.guild_name_text.value = self.guild_name

    def favorites_clicked(self, e) -> None:
        # get data from favorites.json
        favorites = self.load_favorites()

        new_favorite = {"name": self.formated_username, "uuid": self.uuid, "skin_id": self.skin_id}

        if new_favorite not in favorites:
            favorites.append(new_favorite)
            app_logger.info(f"you added {self.formated_username} to favorites!\nuuid: {self.uuid}")
            self.favorite_chip.icon = ft.Icons.FAVORITE_SHARP
            self.favorite_chip.tooltip = "Unfavorite"
            self.favorite_chip.update()
        else:
            favorites.remove(new_favorite)
            app_logger.info(f"you removed {self.formated_username} from favorites")
            self.favorite_chip.icon = ft.Icons.FAVORITE_OUTLINE
            self.favorite_chip.tooltip = "Favorite"
            self.favorite_chip.update()
        
        # write new favorites.json
        self.save_favorites(favorites)
        self.load_favorites_page()
    
    def load_favorites(self) -> list:
        try:
            with open(self.favorites_location, "r", encoding = "utf-8") as file:
                return json.load(file)
            
        except Exception as e:
            app_logger.error(f"Something went while reading favorites.json: {e}")
            return []
    
    def delete_favorite(self, uuid_to_delete) -> None:
        """Deletes a favorite, by uuid"""
        favorites = self.load_favorites()
        for favorite in favorites:
            if favorite["uuid"] == uuid_to_delete:
                app_logger.warning(f"favorite {favorite["name"]} has been removed")
                favorites.remove(favorite)
                break
        self.save_favorites(favorites)
        self.load_favorites_page() # reload favorites
        self.page.update()

    def save_favorites(self, favorites) -> None:
        try:
            with open(self.favorites_location, "w", encoding = "utf-8") as file:
                json.dump(favorites, file, indent = 4)   
        except Exception as e:
            app_logger.error(f"Something went wrong while saving favorites: {e}")

    def load_favorites_page(self) -> None:
        self.favorites_listview.controls.clear()
        favorites = self.load_favorites()
        try:
            for favorite in favorites:
                self.favorites_listview.controls.append(
                    ft.Card(
                        content = ft.Container(
                            ft.Row(controls = [
                                ft.Column(
                                controls = [
                                    ft.Image(src = current_directory / "skin" / f"{favorite["skin_id"]}.png", filter_quality = ft.FilterQuality.NONE, height = 100, fit = ft.ImageFit.FILL),
                                ]
                                ),
                                ft.Column(
                                    controls = [
                                        ft.Text(value = favorite["name"], size = 16),
                                        ft.Text(value = favorite["uuid"], size = 12, color = ft.Colors.GREY_700),
                                        ft.Row(controls = [
                                            ft.Button(text = "See more", on_click = lambda e, uuid = favorite["uuid"]: self.update_contents(uuid)),
                                            ft.Button(text = "Remove", on_click = lambda e, uuid = favorite["uuid"]: self.delete_favorite(uuid))
                                            ]
                                        )
                                    ]
                                )
                            ]
                            ),
                            
                            padding = ft.padding.all(20),
                        )
                    )
                )
        except Exception as e:
            app_logger.error(f"Something went wrong while loading favorites: {e}")
        self.tabs.update()

    def cape_animation_in_thread(self, page_obj, cape_img_control) -> None:
        animator = CapeAnimator(Image.open(current_directory / "cape" / f"{self.cape_id}.png"))
        while animator.get_revealed_pixels() < 160:
            cape_img_control.src_base64 = animator.animate()
            page_obj.update()
            time.sleep(0.04)

    def api_button_click(self, e) -> None:
        if self.api_edit_mode: # this happens after the user clicks has inputted the new api key
            self.api_key_row.controls = [self.api_key_label, self.api_key_display, self.api_key_button] # update the controls to include the entry
            self.hypixel_api_key = self.api_key_entry.value
            self.api_key_display.value = self.hypixel_api_key

            self.api_key_button.text = "Change API Key"

            app_logger.info(f"new api key: {self.hypixel_api_key}")
            try:
                with open(current_directory / ".env", "w") as file:
                    file.write(f'hypixel_api_key = "{self.hypixel_api_key}"')
            except:
                app_logger.error("Couldn't save new .env file containing api key")

            self.api_edit_mode = False
            self.page.update()
        else: # opens the edit menu
            self.api_key_row.controls = [self.api_key_label, self.api_key_entry, self.api_key_button] # update the controls to include the api key text
            self.api_key_button.text = "Save Changes"
            self.api_edit_mode = True
            self.page.update()

    def hypixel_api_switch(self, e) -> None:
        if self.enable_hypixel.value == True:
            self.hypixel_integration_enabled = True
            self.guild_list_view.visible = True
            self.page.update()
            app_logger.info("Switched hypixel integration to ON")
        else:
            self.hypixel_integration_enabled = False
            self.hypixel_info_card.visible = False
            self.guild_list_view.visible = False
            self.page.update()
            app_logger.info("Switched hypixel integration to OFF")
            
    def dismiss_no_api_key_banner(self, e) -> None:
        self.page.close(self.no_api_key_banner)
        self.user_dismissed_no_api_banner = True

    def switch_theme(self, e) -> None:
        if self.app_theme_dark_switch.value:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.app_theme_light = False
            self.enable_gradient = True
            self.page.update()
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.app_theme_light = True
            self.enable_gradient = False
            self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT]) # resets gradient
            self.page.update()


def main_entry_point(page: ft.Page):
    app_instance = FakeMCApp(page)

    for file in os.listdir(current_directory / "cape"):
        if "raw" not in file and "no_cape" not in file and "back" not in file:
            app_instance.create_cape_showcase(file)
    page.update()

    app_instance.load_favorites_page()

ft.app(target = main_entry_point)

