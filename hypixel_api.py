import requests
import datetime
from dotenv import load_dotenv
import os
import json

load_dotenv()
rank_map = {
    "VIP": "VIP",
    "VIP_PLUS": "VIP+",
    "MVP": "MVP",
    "MVP_PLUS": "MVP+"
}


class getHypixelData:
    def __init__(self, uuid, hypixel_api_key):
        self.uuid = uuid
        self.api_key = hypixel_api_key

    def get_basic_data(self):
        """
        requires uuid and api key
        returns first login date (as month/year format) and player rank
        returns None if player is not found
        """
        payload = {
            "uuid": self.uuid
        }

        try:
            player_data = requests.get(
                url = "https://api.hypixel.net/v2/player",
                params = payload,
                headers = {"API-Key": self.api_key}
                )
            
            player_data.raise_for_status()

            json_player_data = player_data.json()

            first_login_formatted = None
            player_rank = None



        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occured: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request exception occured: {e}")
        except Exception as e:
            print(f"something went wrong while getting Hypixel player data: {e}")
            return False
        try:
            with open("hypixel_player_data.json", "w", encoding="utf-8") as file:
                json.dump(json_player_data, file, indent = 4)

            first_login = json_player_data["player"]["firstLogin"] / 1000 # transforms to standard (non miliseconds) UNIX time
            first_login_formatted = datetime.datetime.fromtimestamp(first_login).strftime("%m/%Y")
            player_rank = json_player_data["player"]["newPackageRank"]

            try:
                player_rank_formatted = rank_map[player_rank]
            except KeyError:
                player_rank_formatted = player_rank

            return first_login_formatted, player_rank_formatted
        except KeyError:
            print("player has no rank")
            return first_login_formatted, "no rank"
        except Exception as e:
            print(f"Something went wrong while proccessing Hypixel data: {e}")
            return None, None

    def get_guild_info(self):
        """
        requires uuid and api key
        returns a list with a specified number of guild members
        """
        try:
            payload = {"player": self.uuid}

            guild_response = requests.get(
                url = "https://api.hypixel.net/v2/guild",
                params = payload,
                headers = {"API-Key": self.api_key}
            )

            guild_response.raise_for_status()

            print(guild_response)
            if guild_response.json()["guild"] == None:
                print("no guild")
                return None
            
            members = guild_response.json()["guild"]["members"]
            guild_members = []
            for index, member in enumerate(members):
                if index < 10: # gets the first x members of the guild
                    guild_members.append(member["uuid"])

            return guild_members
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occured: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request exception occured: {e}")
        except KeyError as e:
            print(f"coudn't find {e}")
        except Exception as e:
            print(f"something went wrong while getting hypixel guild info: {e}")


if __name__ == "__main__":
    uuid = "bb3c62c3428340789779d1b0db7a7743"
    hypixel_api_key = os.getenv("hypixel_api_key")

    user = getHypixelData(uuid, hypixel_api_key)
    #user.get_basic_data()
    user.get_guild_info()