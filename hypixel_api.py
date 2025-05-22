import requests
import datetime
from dotenv import load_dotenv
import os
import json
import logging

logger = logging.getLogger(__name__)

load_dotenv()
rank_map = {
    "VIP": "VIP",
    "VIP_PLUS": "VIP+",
    "MVP": "MVP",
    "MVP_PLUS": "MVP+",
    "YOUTUBER": "YouTube"
}

MAX_GUILD_MEMBERS_TO_FETCH = 15


class getHypixelData:
    def __init__(self, uuid, hypixel_api_key):
        self.uuid = uuid
        self.api_key = hypixel_api_key

    def get_basic_data(self):
        """
        requires uuid and api key
        returns first login date (as month/year format) and player rank
        returns None, None if player is not found
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
            logger.error(f"HTTP error occured: {e}")
            return None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception occured: {e}")
            return None, None
        except Exception as e:
            logger.warning(f"something went wrong while getting Hypixel player data: {e}")
            return None, None
        
        try:
            with open("hypixel_player_data.json", "w", encoding="utf-8") as file:
                json.dump(json_player_data, file, indent = 4)
        except Exception as e:
            logger.error(f"Something went wrong while proccessing Hypixel data: {e}")
            return None, None
        
        try:
            first_login = json_player_data["player"]["firstLogin"] / 1000 # transforms to standard (non miliseconds) UNIX time
            first_login_formatted = datetime.datetime.fromtimestamp(first_login).strftime("%m/%Y")
        except Exception as e:
            logger.warning(f"something went wrong with first login date: {e}")
            return None, None
        
        try:
            player_rank = json_player_data["player"]["rank"]
        except:
            try:
                player_rank = json_player_data["player"]["newPackageRank"]
            except KeyError:
                logger.info("player has no rank")
                return first_login_formatted, "no rank"
        
        try:
            player_rank_formatted = rank_map[player_rank]
            logger.info(f"player rank: {player_rank_formatted}")
        except KeyError:
            player_rank_formatted = player_rank
            logging.warning(f"rank not identified: {player_rank_formatted}")
        return first_login_formatted, player_rank_formatted
        

    def get_guild_info(self):
        """
        requires uuid and api key
        returns a list with a specified number of guild members
        return None if it fails
        """
        try:
            payload = {"player": self.uuid}

            guild_response = requests.get(
                url = "https://api.hypixel.net/v2/guild",
                params = payload,
                headers = {"API-Key": self.api_key}
            )

            guild_response.raise_for_status()

            logger.debug(guild_response)
            if guild_response.json()["guild"] == None:
                logger.info("no guild")
                return None
            
            members = guild_response.json()["guild"]["members"]
            guild_members = []
            for index, member in enumerate(members):
                if index < MAX_GUILD_MEMBERS_TO_FETCH: # gets the first x members of the guild
                    guild_members.append(member["uuid"])

            return guild_members
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occured: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception occured: {e}")
            return None
        except KeyError as e:
            logger.warning(f"coudn't find {e}")
            return None
        except Exception as e:
            logger.warning(f"something went wrong while getting hypixel guild info: {e}")
            return None


if __name__ == "__main__":
    uuid = "bb3c62c3428340789779d1b0db7a7743"
    hypixel_api_key = os.getenv("hypixel_api_key")

    user = getHypixelData(uuid, hypixel_api_key)
    #user.get_basic_data()
    user.get_guild_info()