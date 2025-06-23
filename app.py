from minecraft_api import GetMojangAPIData
from hypixel_api import GetHypixelData
from cape_animator import CapeAnimator
from online_status import OnlineStatus
from cache_manager import CacheManager
from data_manager import DataManager
from utils import pillow_to_b64, load_base64_to_pillow
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

        self.current_mojang_data = None

        # variables for settings
        self.completed_onboarding_flow = None
        self.settings = []
        self.favorites_location = current_directory / "favorites.json"
        self.settings_location = current_directory / "config.json"
        
        if Path.exists(self.settings_location):
            try:
                self.settings = self.load_settings()
                self.app_theme_light = self.settings["light_theme"]
                if self.app_theme_light:
                    self.page.theme_mode = ft.ThemeMode.LIGHT
                else:
                    self.page.theme_mode = ft.ThemeMode.DARK
                self.hypixel_integration_enabled = self.settings["hypixel_integration"]
                self.guild_members_to_fetch = self.settings["max_guild_members"]
                self.completed_onboarding_flow = self.settings["completed_onboarding_flow"]
            except Exception as e:
                app_logger.warning(f"Something went wrong, resetting to defaults: {e}")
                self.settings = {}
                # uses defaults
                self.guild_members_to_fetch = 15
                self.hypixel_integration_enabled = True # enables or disables Hypixel integration
                self.completed_onboarding_flow = True
                self.save_settings()
        else:
            app_logger.info("No config file detected")
            self.completed_onboarding_flow = False
            self.hypixel_integration_enabled = False
            self.guild_members_to_fetch = 15
        

        if self.page.platform_brightness == ft.Brightness.LIGHT: # disables gradient if theme is light
            self.enable_gradient = False
            self.app_theme_light = True
        else:
            self.app_theme_light = False

        self.api_edit_mode = False # for config tab, changes api_key to be editable
        self.enable_gradient = True
        self.user_dismissed_no_api_banner = False # once this is True, banner will no longer be shown


        # flet ui starts here
        if self.completed_onboarding_flow:
            self.load_main_ui()
        else:
            self.load_setup_tab_1()

    def get_data_from_button(self, e) -> None:
        data_entered = self.username_entry.value.strip()
        self.update_contents(data_entered)

    def load_ui_tab_1(self):
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

        self.data_status_icon = ft.Icon("CACHED", color = ft.Colors.YELLOW_700, tooltip = "Data loaded from cache", visible = False)

        self.data_status_icon_c = ft.Container(content = self.data_status_icon, padding = ft.padding.only(top = 5))

        self.favorite_chip_c = ft.Container(content = self.favorite_chip, padding = ft.padding.only(top = 5))

        self.username_row = ft.Row(controls = [self.formated_username_text, self.favorite_chip_c, self.data_status_icon_c])

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
        self.player_status_icon = ft.Icon(name = ft.Icons.CIRCLE_ROUNDED, color = ft.Colors.GREY_700)
        self.player_status_icon_c = ft.Container(content = self.player_status_icon, padding = ft.padding.only(top = 5))
        self.player_status_text = ft.Text(value = "")
        self.player_status_row = ft.Row(controls = [self.player_status_icon_c, self.player_status_text])

        self.hypixel_info_card = ft.Card(content = ft.Container(
            content = ft.Column(
                controls= [self.first_login_text, self.player_rank_text, self.player_status_row]
                ),
            padding = ft.padding.all(20),
            alignment=ft.alignment.top_center
            ),
            elevation = 1,
            margin = ft.padding.only(right = 60),
            visible = False
        )

        self.guild_name_text = ft.Text(value = "", text_align = ft.TextAlign.CENTER, size = 16)
        self.guild_list_view = ft.ListView(spacing = 10, width = 200, height = 450, auto_scroll = True)
        self.guild_col = ft.Column(controls = [self.guild_name_text, self.guild_list_view], horizontal_alignment = ft.CrossAxisAlignment.CENTER)
        self.guild_list_c = ft.Container(content = self.guild_col, margin = ft.margin.only(bottom = 50, right = 30))

        self.img_displays = ft.Row(controls = [self.skin_showcase_img, self.cape_showcase_img_c, self.cape_name], alignment=ft.alignment.top_center)
        self.img_displays_c = ft.Container(padding = ft.padding.only(150, 10), content = self.img_displays)

        self.hypixel_display = ft.Row(controls = [self.hypixel_info_card, self.guild_list_c], vertical_alignment=ft.CrossAxisAlignment.START)

        self.main_info = ft.Row(controls=[self.img_displays_c, self.hypixel_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)

        return ft.Column(controls = [self.search_c, self.info_c, self.main_info])

    def load_ui_tab_4(self):
        self.app_theme_dark_switch = ft.Switch(label = " Dark Theme", on_change = self.switch_theme, value = not self.app_theme_light)

        self.settings_divider = ft.Divider()

        self.enable_hypixel = ft.Switch(label = " Hypixel API integration", on_change = self.hypixel_api_switch, value = self.hypixel_integration_enabled)

        self.api_key_label = ft.Text("Current Hypixel API Key: ") # a label
        self.api_key_display = ft.Text(self.hypixel_api_key, selectable = True) # displays the actual key
        self.api_key_entry = ft.TextField(hint_text = "Hypixel API Key", on_submit = self.api_button_click)
        self.api_key_button = ft.Button(text = "Change API Key", on_click = self.api_button_click)

        self.api_key_row = ft.Row(controls = [self.api_key_label, self.api_key_display, self.api_key_button])

        self.guild_members_to_fetch_text = ft.Text(value = "Max guild members to load")
        self.guild_members_to_fetch_input = ft.TextField(
            keyboard_type = ft.KeyboardType.NUMBER,
            input_filter = ft.NumbersOnlyInputFilter(),
            value = str(self.guild_members_to_fetch),
            on_change = self.update_guild_members_to_fetch,
            width = 50
        )
        self.guild_members_to_fetch_info = ft.Icon(name = ft.Icons.INFO_OUTLINE_ROUNDED, tooltip = "Very high values can cause rate limits")

        self.guild_members_to_fetch_row = ft.Row(controls = [self.guild_members_to_fetch_text, self.guild_members_to_fetch_input, self.guild_members_to_fetch_info])

        return ft.Column(controls = [self.app_theme_dark_switch, self.settings_divider, self.enable_hypixel, self.api_key_row, self.guild_members_to_fetch_row])

    def load_setup_tab_1(self):
        # these are the elements for the onboarding tab
        self.setup_header_text = ft.Text(
            spans = [
                ft.TextSpan(
                    text = "Welcome to FakeMC",
                    style = ft.TextStyle(
                        size = 36,
                        foreground = ft.Paint(
                            gradient = ft.PaintLinearGradient(
                                begin = (450, 0),
                                end = (1000, 0),
                                colors = [ft.Colors.PURPLE_300, ft.Colors.BLUE_300]
                            ),
                            style = ft.PaintingStyle.FILL
                        )
                    )
                )
            ],
            text_align = ft.TextAlign.CENTER,
            width = 600
        )
        
        self.setup_subheader_text = ft.Text("Let's personalise your experience", size = 24, text_align = ft.TextAlign.CENTER, width = 600)
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.setup_headers_col = ft.Column(controls = [self.setup_header_text, self.setup_subheader_text])
        self.setup_start_button = ft.Button(text = "Let's start", on_click = self.load_setup_tab_2, style = ft.ButtonStyle(
            padding = 20
        ))
        self.setup_start_button_c = ft.Container(content = self.setup_start_button, padding = 20)

        self.setup_column = ft.Column(
            controls = [self.setup_headers_col, self.setup_start_button_c],
            horizontal_alignment = ft.CrossAxisAlignment.CENTER,
            alignment = ft.MainAxisAlignment.SPACE_AROUND,
            expand = True
            )
        self.setup_column_c = ft.Container(content = self.setup_column, alignment = ft.alignment.top_center)
        self.page.add(self.setup_column)

    def load_setup_tab_2(self, e):
        app_logger.info(f"loading page 2 of setup")
        self.page.controls.clear()
        self.page.update()
        
        self.setup_choose_theme_header = ft.Text("Choose a theme", text_align = ft.TextAlign.CENTER, size = 24)
        self.setup_light_theme_container = ft.Container(
            content = ft.Text("Light Theme", color = ft.Colors.BLACK),
            width = 200, height = 200, ink = True, alignment = ft.alignment.center,
            bgcolor = ft.Colors.WHITE, border_radius = 15,
            on_click = lambda e, theme_to_apply = "light": self.apply_theme(theme_to_apply),
            margin = 20
            )
        
        self.setup_dark_theme_container = ft.Container(
            content = ft.Text("Dark Theme", color = ft.Colors.WHITE),
            width = 200, height = 200, ink = True, alignment = ft.alignment.center,
            bgcolor = ft.Colors.GREY_900, border_radius = 15,
            on_click = lambda e, theme_to_apply = "dark": self.apply_theme(theme_to_apply),
            margin = 20
            )
        
        self.setup_themes_row = ft.Row(controls = [self.setup_light_theme_container, self.setup_dark_theme_container], alignment = ft.MainAxisAlignment.CENTER,)

        self.setup_themes_button = ft.Button(text = "Continue", on_click = self.load_setup_tab_3, style = ft.ButtonStyle(
            padding = 20
        ))

        self.setup_themes_column = ft.Column(
            controls = [self.setup_choose_theme_header, self.setup_themes_row, self.setup_themes_button],
            alignment = ft.MainAxisAlignment.SPACE_AROUND,
            expand = True,
            horizontal_alignment = ft.CrossAxisAlignment.CENTER
            )
        self.page.add(self.setup_themes_column)

    def load_setup_tab_3(self, e):
        app_logger.info(f"loading page 3 of setup")
        self.page.controls.clear()
        self.page.update()

        self.setup_hypixel_header = ft.Text("Enable Hypixel integration?", size = 24)
        self.setup_hypixel_info = ft.Text(
            "Hypixel integration requires an API key. You can get one from ",
            spans = [
                ft.TextSpan(
                    "Hypixel Developer Dashboard",
                    style = ft.TextStyle(
                        color = ft.Colors.BLUE_800,
                    ),
                    url = "https://developer.hypixel.net/dashboard/"
                ),
                ft.TextSpan(
                    ", but it will expire after 24 hours."
                ),
                ft.TextSpan(
                    "\n\nYou can add one here, or skip this step and add one later."
                )
            ]
            )

        self.setup_hypixel_first_col = ft.Column(controls = [self.setup_hypixel_info], width = 450)

        self.setup_hypixel_switch = ft.Switch(label = "Enable Hypixel Integration", on_change = self.setup_hypixel_api_switch_changed)
        self.setup_hypixel_api_entry = ft.TextField(disabled = True, on_submit = self.check_hypixel_key)
        self.setup_hypixel_check_button = ft.Button(text = "Check Key", on_click = self.check_hypixel_key, disabled = True)
        self.setup_hypixel_test_result = ft.Text("")

        self.setup_hypixel_api_row = ft.Row(controls = [self.setup_hypixel_api_entry, self.setup_hypixel_check_button])

        self.setup_hypixel_second_col = ft.Column(
            controls = [self.setup_hypixel_switch, self.setup_hypixel_api_row, self.setup_hypixel_test_result],
            horizontal_alignment = ft.CrossAxisAlignment.CENTER
            )

        self.setup_hypixel_content_row = ft.Row(controls = [self.setup_hypixel_first_col, self.setup_hypixel_second_col], alignment = ft.MainAxisAlignment.SPACE_AROUND)

        self.setup_hypixel_button = ft.Button(text = "Skip", on_click = self.load_setup_tab_4, style = ft.ButtonStyle(
            padding = 20
        ))

        self.setup_hypixel_col = ft.Column(
            controls = [self.setup_hypixel_header, self.setup_hypixel_content_row, self.setup_hypixel_button],
            expand = True,
            horizontal_alignment = ft.CrossAxisAlignment.CENTER,
            alignment = ft.MainAxisAlignment.SPACE_AROUND
        )

        self.page.add(self.setup_hypixel_col)
    
    def load_setup_tab_4(self, e):
        if self.setup_hypixel_switch.value == False:
            app_logger.info("Hypixel integration is disabled")
            self.hypixel_integration_enabled = False
            self.save_settings()
            self.hypixel_api_key = ""
            app_logger.info(f"new api key: {self.hypixel_api_key}")
            try:
                with open(current_directory / ".env", "w") as file:
                    file.write(f'hypixel_api_key = "{self.hypixel_api_key}"')
            except Exception as e:
                app_logger.error(f"Couldn't save new .env file containing api key: {e}")
        self.page.controls.clear()
        self.page.update()

        self.setup_finish_header = ft.Text(value = "You're done! You can now enjoy the app", size = 24)
        self.setup_finish_button = ft.Button(text = "Finish", on_click = self.finish_setup, style = ft.ButtonStyle(
            padding = 20
        ))

        self.setup_finish_col = ft.Column(
            controls = [self.setup_finish_header, self.setup_finish_button],
            alignment = ft.MainAxisAlignment.SPACE_AROUND,
            horizontal_alignment = ft.CrossAxisAlignment.CENTER,
            expand = True
            )

        self.page.add(self.setup_finish_col)

    def load_main_ui(self):
        self.home_page = self.load_ui_tab_1()        

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
        self.config_col = self.load_ui_tab_4()

        # no api key banner
        self.no_api_key_banner = ft.Banner(
            content = ft.Text(value = "You didn't enter a Hypixel API Key. Please enter one in Settings. Hypixel integration requires an API Key"),
            actions = [
                ft.TextButton(text = "Ignore", on_click = self.dismiss_no_api_key_banner)
            ]
        )

        self.hypixel_request_error_banner = ft.Banner(
            content=ft.Text(value="Your Hypixel API key is invalid. Please update it in Settings or disable Hypixel integration."),
            actions=[
                ft.TextButton(text = "Ignore", on_click = self.dismiss_invalid_api_key_banner)
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
                self.cape_showcase_img.src_base64 = self.current_mojang_data["cape_back_b64"]
                self.cape_showcase_img.update()
        else:
            if self.has_cape:
                self.cape_showcase_img.src_base64 = self.current_mojang_data["cape_showcase_b64"]
                self.cape_showcase_img.update()

    def update_contents(self, data_entered) -> None:
        """
        handles updating the ui, including managing animations
        req data_entered (minecraft username or uuid)
        """

        self.tabs.selected_index = 0

        app_logger.info(f"data entered: {data_entered}")

        self.skin_showcase_img.scale = 0.3
        self.page.update()

        mojang_data_instance = DataManager(self.hypixel_api_key)
        mojang_data = mojang_data_instance.get_mojang_data(data_entered)
        app_logger.info(mojang_data)

        if mojang_data["status"] == "success":
            app_logger.info(f"success for getting mojang data: {mojang_data['status']}")
            self.formated_username_text.value = mojang_data['username']
            self.uuid_text.value = f"uuid: {mojang_data['uuid']}"
            self.skin_showcase_img.scale = 1 # animates skin showcase img
            self.player_status_text.value = ""
            self.skin_showcase_img.src_base64 = mojang_data['skin_showcase_b64']
            
            if mojang_data['has_cape']:
                self.has_cape = True
                app_logger.info(f"{mojang_data['username']} has cape: {mojang_data['cape_name']}")
                self.cape_name.value = mojang_data['cape_name']
                self.animate_cape(mojang_data)
                self.update_gradient(mojang_data)
            else:
                self.has_cape = False
                app_logger.info(f"{mojang_data['username']} has no cape")
                self.cape_showcase_img.src_base64 = pillow_to_b64(Image.open(current_directory / "cape" / "no_cape.png"))
                self.cape_name.value = ""
                self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])
                self.page.update()

            # store current state for cape hover and favorites
            self.current_mojang_data = mojang_data

            # cache icon management
            if mojang_data["source"] == "cache":
                self.data_status_icon.visible = True
                self.data_status_icon.name = "CACHED"
                self.data_status_icon.tooltip = "Data loaded from cache"
                self.data_status_icon.color = ft.Colors.YELLOW_700
            elif mojang_data["source"] == "mojang_api":
                self.data_status_icon.visible = True
                self.data_status_icon.name = "CLOUD_DOWNLOAD"
                self.data_status_icon.tooltip = "Data loaded from Mojang API"
                self.data_status_icon.color = ft.Colors.GREEN_800

            self.page.update()
        else:
            app_logger.info(f"status for mojang data: {mojang_data['status']}")
            self.reset_controls()

        # checks if user is in favorites
        favorites = self.load_favorites()
        if mojang_data["status"] == "success":
            self.favorite_chip.visible = True
            for favorite in favorites:
                if favorite["uuid"] == mojang_data["uuid"]:
                    self.favorite_chip.icon = ft.Icons.FAVORITE_SHARP
                    self.favorite_chip.tooltip = "Unfavorite"
                    break
            else:
                self.favorite_chip.icon = ft.Icons.FAVORITE_OUTLINE
                self.favorite_chip.tooltip = "Favorite"
        else:
            self.favorite_chip.visible = False
        self.page.update()

        if self.hypixel_api_key is not None and self.hypixel_api_key != "":
            if self.hypixel_integration_enabled:
                app_logger.info(f"accessing hypixel api with api key: ****{self.hypixel_api_key[-4:]}")
                self.load_hypixel_data(mojang_data) 
            else:
                app_logger.info("hypixel integration is currently disabled")
        else:
            if self.hypixel_integration_enabled:
                if not self.user_dismissed_no_api_banner: # only shows banner if it hasn't already been dismissed by the user
                    self.page.open(self.no_api_key_banner)
                self.guild_list_view.controls.clear()
                self.hypixel_info_card.visible = False
                self.guild_name_text.value = ""

        
        status = self.get_online_status(mojang_data)
        app_logger.info(f"{mojang_data["username"]}'s status: {status}")
        if status == "Hypixel":
            self.player_status_text.value = "Online (Hypixel)"
            self.player_status_icon.color = ft.Colors.GREEN_800
        elif status == "Wynncraft":
            self.player_status_text.value = "Online (Wynncraft)"
            self.player_status_icon.color = ft.Colors.GREEN_800
        elif status == "offline":
            self.player_status_text.value = "Offline"
            self.player_status_icon.color = ft.Colors.GREY_700
        else:
            self.player_status_text.value = "Unknown"
        self.page.update()
        
    def animate_cape(self, mojang_data) -> None:
        animation_thread = threading.Thread(
            target = self.cape_animation_in_thread,
                args = (
                    self.page,
                    self.cape_showcase_img,
                    mojang_data["cape_showcase_b64"],
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
        self.guild_name_text.value = ""
        self.player_status_text.value = ""
        self.guild_list_view.controls.clear()
        self.hypixel_info_card.visible = False
        self.data_status_icon.visible = False
        self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])

    def update_gradient(self, mojang_data: dict) -> None:
        cape_pillow = load_base64_to_pillow(mojang_data["cape_showcase_b64"])
        bgcolor_instance = CapeAnimator(cape_pillow)
        bgcolor = bgcolor_instance.get_average_color_pil()
        if bgcolor is not None and self.enable_gradient:
            self.home_page_container.gradient = ft.RadialGradient(colors = [bgcolor, ft.Colors.TRANSPARENT], center = ft.Alignment(-0.35, 0), radius = 0.7) # handle gradient color
        else:
            self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT])
            app_logger.warning("Cape color not found")
        self.page.update()

    def load_hypixel_data(self, mojang_data: dict) -> None:
        # --- Hypixel api integration ---
        if mojang_data["uuid"] is not None:
            self.hypixel_info_card.content.content = ft.ProgressRing()
            self.first_login_text.value = ""
            self.player_rank_text.value = ""
            self.hypixel_info_card.visible = True
            self.guild_name_text.value = ""
            self.guild_list_view.controls.clear()
            self.page.update()
            hypxiel_data_instance = DataManager(self.hypixel_api_key)
            hypixel_data = hypxiel_data_instance.get_hypixel_data(mojang_data["uuid"], self.guild_members_to_fetch)
            if hypixel_data["status"] == "success":
                if hypixel_data["first_login"] is not None and hypixel_data["player_rank"] is not None:
                    app_logger.info("displaying hypixel info card")
                    self.hypixel_info_card.content.content = ft.Column(
                        controls= [self.first_login_text, self.player_rank_text, self.player_status_row]
                        )
                    self.hypixel_info_card.visible = True
                    self.first_login_text.value = f"Account first seen on: {hypixel_data["first_login"]}"
                    self.player_rank_text.value = f"Player rank: {hypixel_data["player_rank"]}"
                    self.page.update()
                else:
                    self.hypixel_info_card.content.content = ft.Column(
                        controls= [self.first_login_text, self.player_rank_text, self.player_status_row]
                        )
                    self.hypixel_info_card.visible = False
                    self.first_login_text.value = ""
                    self.player_rank_text.value = ""
                    self.guild_name_text.value = ""
                    self.page.update()
            # error handling
            elif hypixel_data["status"] == "invalid_api_key":
                self.hypixel_request_error_banner.content.value = f"Your Hypixel API key is invalid. Please update it in Settings or disable Hypixel integration."
                self.page.open(self.hypixel_request_error_banner)
            elif hypixel_data["status"] == "http_error":
                self.hypixel_request_error_banner.content.value = f"An unexpected HTTP error occurred: {hypixel_data["status"]}"
            elif hypixel_data["status"] == "request_error":
                self.hypixel_request_error_banner.content.value = f"An unexpected Request error occurred: {hypixel_data["status"]}"
            elif hypixel_data["status"] == "unknown_error":
                self.hypixel_request_error_banner.content.value = f"An unexpected error occurred: {hypixel_data["status"]}"
            else:
                self.hypixel_request_error_banner.content.value = f"An unexpected error occurred."
                app_logger.error(f"Didn't receive all arguments for get_basic_data from class GetHypixelData")
            
            if hypixel_data["guild_name"] is None:
                self.guild_name_text.value = ""
            app_logger.debug(hypixel_data["guild_members"])
            app_logger.info(f"{mojang_data["username"]}'s guild is {hypixel_data["guild_name"]}")
        else:
            self.guild_list_view.controls.clear()
            self.page.update()
            return

        if hypixel_data["guild_members"] is None:
            self.guild_list_view.controls.clear()
            self.page.update()
            self.guild_name_text.value = ""

        if hypixel_data["guild_members"] is not None:
            self.guild_list_view.controls.clear()
            for member in hypixel_data["guild_members"]:
                guild_member_name = member["name"]
                if guild_member_name is not None:
                    self.guild_list_view.controls.append(
                        ft.Button(
                            text = guild_member_name,
                            on_click = lambda e, name_to_pass = member["uuid"]: self.update_contents(name_to_pass)
                        )
                    )
                self.guild_name_text.value = hypixel_data["guild_name"]
                self.page.update()

    def get_online_status(self, mojang_data) -> str:
        active_user_status = OnlineStatus(mojang_data["username"], mojang_data["uuid"], self.hypixel_api_key) # TODO UPDATE THIS TO USE NEW DATA FROMAT
        return active_user_status.start_requests()

    # favorites
    def favorites_clicked(self, e) -> None:
        # get data from favorites.json
        favorites = self.load_favorites()

        new_favorite = {
            "uuid": self.current_mojang_data["uuid"],
            "username": self.current_mojang_data["username"],
            "skin_b64": self.current_mojang_data["skin_showcase_b64"],
            }

        if new_favorite not in favorites:
            favorites.append(new_favorite)
            app_logger.info(f"you added {self.current_mojang_data["username"]} to favorites!\nuuid: {self.current_mojang_data["uuid"]}")
            self.favorite_chip.icon = ft.Icons.FAVORITE_SHARP
            self.favorite_chip.tooltip = "Unfavorite"
            self.favorite_chip.update()
        else:
            favorites.remove(new_favorite)
            app_logger.info(f"you removed {self.current_mojang_data["username"]} from favorites")
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
                app_logger.warning(f"favorite {favorite["username"]} has been removed")
                favorites.remove(favorite)
                break
        self.save_favorites(favorites)
        self.load_favorites_page() # reload favorites
        self.page.update()

    def save_favorites(self, favorites: dict) -> None:
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
                                    ft.Image(src_base64 = favorite["skin_b64"], filter_quality = ft.FilterQuality.NONE, height = 100, fit = ft.ImageFit.FILL),
                                ]
                                ),
                                ft.Column(
                                    controls = [
                                        ft.Text(value = favorite["username"], size = 16),
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

    def cape_animation_in_thread(self, page_obj, cape_img_control, cape_b64) -> None:
        animator = CapeAnimator(load_base64_to_pillow(cape_b64))
        while animator.get_revealed_pixels() < 160:
            cape_img_control.src_base64 = animator.animate()
            page_obj.update()
            time.sleep(0.04)

    # methods for settings
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
            except Exception as e:
                app_logger.error(f"Couldn't save new .env file containing api key: {e}")

            self.api_edit_mode = False
            self.page.update()
        else: # opens the edit menu
            self.api_key_row.controls = [self.api_key_label, self.api_key_entry, self.api_key_button] # update the controls to include the api key text
            self.api_key_button.text = "Save Changes"
            self.api_edit_mode = True
            self.page.update()

    def hypixel_api_switch(self, e) -> None:
        if self.enable_hypixel.value:
            self.hypixel_integration_enabled = True
            self.guild_list_view.visible = True
            self.page.update()
            app_logger.info("Switched hypixel integration to ON")
            self.save_settings()
        else:
            self.hypixel_integration_enabled = False
            self.hypixel_info_card.visible = False
            self.guild_list_view.visible = False
            self.guild_name_text.value = ""
            self.page.update()
            app_logger.info("Switched hypixel integration to OFF")
            self.save_settings()
 
    def dismiss_no_api_key_banner(self, e) -> None:
        self.page.close(self.no_api_key_banner)
        self.user_dismissed_no_api_banner = True

    def dismiss_invalid_api_key_banner(self, e) -> None:
        self.page.close(self.hypixel_request_error_banner)

    def switch_theme(self, e) -> None:
        if self.app_theme_dark_switch.value:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.app_theme_light = False
            self.enable_gradient = True
            self.page.update()
            self.settings["light_theme"] = False
            self.save_settings()
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.app_theme_light = True
            self.enable_gradient = False
            self.home_page_container.gradient = ft.RadialGradient(colors = [ft.Colors.TRANSPARENT, ft.Colors.TRANSPARENT]) # resets gradient
            self.page.update()
            self.settings["light_theme"] = True
            self.save_settings()

    def update_guild_members_to_fetch(self, e) -> None:
        if self.guild_members_to_fetch_input.value != "":
            self.guild_members_to_fetch = int(self.guild_members_to_fetch_input.value)
        else:
            self.guild_members_to_fetch = 0

        self.settings["max_guild_members"] = self.guild_members_to_fetch
        self.save_settings()
        app_logger.info(f"Updated guild members to fetch: {self.guild_members_to_fetch}")

    # settings 
    def save_settings(self) -> None:
        settings = {
            "light_theme": self.app_theme_light,
            "max_guild_members": self.guild_members_to_fetch,
            "hypixel_integration": self.hypixel_integration_enabled,
            "completed_onboarding_flow": self.completed_onboarding_flow
            }
        with open(self.settings_location, "w") as file:
            json.dump(settings, file, indent = 4)
        
    def load_settings(self) -> dict:
        with open(self.settings_location, "r") as file:
            settings = json.load(file)
            app_logger.info(f"loaded settings: {settings}")
            return settings

    # methods for onboarding
    def apply_theme(self, theme_to_apply) -> None:
        if theme_to_apply == "light":
            self.app_theme_light = True
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.update()
            self.save_settings()    
            app_logger.info("selected light theme")
        elif theme_to_apply == "dark":
            self.app_theme_light = False
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.update()
            self.save_settings()
            app_logger.info("selected dark theme")

    def setup_hypixel_api_switch_changed(self, e):
        if self.setup_hypixel_switch.value == True:
            self.setup_hypixel_api_entry.disabled = False
            self.setup_hypixel_button.disabled = True
            self.setup_hypixel_check_button.disabled = False
            self.setup_hypixel_button.text = "Continue"
            self.page.update()
        elif self.setup_hypixel_switch.value == False:
            self.setup_hypixel_api_entry.disabled = True
            self.setup_hypixel_button.disabled = False
            self.setup_hypixel_check_button.disabled = True
            self.setup_hypixel_button.text = "Skip"
            self.page.update()
    
    def check_hypixel_key(self, e):
        api_key_entered = self.setup_hypixel_api_entry.value
        test_api_instance = GetHypixelData("f7c77d999f154a66a87dc4a51ef30d19", api_key_entered) # tries to get info about player Hypixel as test
        _, _, result = test_api_instance.get_basic_data()
        if result == "success":
            app_logger.info("Test Api request was successful")
            self.hypixel_api_key = api_key_entered
            self.hypixel_integration_enabled = True
            self.save_settings()
            app_logger.info("Hypixel integration is enabled")
            self.setup_hypixel_button.disabled = False
            self.setup_hypixel_test_result.color = ft.Colors.GREEN_700

            app_logger.info(f"new api key: {self.hypixel_api_key}")
            try:
                with open(current_directory / ".env", "w") as file:
                    file.write(f'hypixel_api_key = "{self.hypixel_api_key}"')
            except Exception as e:
                app_logger.error(f"Couldn't save new .env file containing api key: {e}")

            self.setup_hypixel_test_result.value = "Request was successful!"
            self.page.update()
        else:
            self.setup_hypixel_test_result.color = ft.Colors.RED_700
            self.setup_hypixel_test_result.value = "Request was unsuccessful. Try checking again in ~20 seconds\nYou can also disable integration and skip this for now"
            app_logger.info("Test Api request was unsuccessful")
            self.page.update()

    def finish_setup(self, e):
        self.completed_onboarding_flow = True
        self.save_settings()
        app_logger.info("Completed setup flow")
        self.page.controls.clear()
        self.load_main_ui()
        for file in os.listdir(current_directory / "cape"):
            if "raw" not in file and "no_cape" not in file and "back" not in file:
                self.create_cape_showcase(file)
        self.load_favorites_page()
        self.page.update()

def main_entry_point(page: ft.Page):
    app_instance = FakeMCApp(page)

    if app_instance.completed_onboarding_flow:
        for file in os.listdir(current_directory / "cape"):
            if "raw" not in file and "no_cape" not in file and "back" not in file:
                app_instance.create_cape_showcase(file)
        page.update()

        app_instance.load_favorites_page()

ft.app(target = main_entry_point)