from cache_manager import CacheManager
from hypixel_api import GetHypixelData
from minecraft_api import GetMojangAPIData
from online_status import OnlineStatus
from utils import load_base64_to_pillow
import logging
import os
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, hypixel_api_key: str):
        self.hypixel_api_key = hypixel_api_key
        self.cache_instance = CacheManager()

    def get_mojang_data(self, search_term: str) -> dict:
        """
        Fetches Mojang data for a given username or UUID.
        returns a dictionary with the following keys
        - status: "success", "lookup_failed", or "failed"
        - source: "mojang_api" or "cache"
        - uuid: the UUID of the player
        - username: the formatted username of the player
        - has_cape: boolean indicating if the player has a cape
        - cape_name: the name of the cape if the player has one, otherwise None
        - skin_showcase_b64: base64 encoded string of the player's skin showcase
        - cape_showcase_b64: base64 encoded string of the player's cape showcase
        - cape_back_b64: base64 encoded string of the player's cape back image
        """

        status = "error"
        source = None
        
        valid_cache = self.cache_instance.check_mojang_cache(search_term, 120)
        logger.info(f"valid cache for {search_term}: {valid_cache}")
        if not valid_cache: # if cache is not valid, it will update the cache
            if len(search_term) <= 16: # if text inputted is less than 16 chars (max username length) search is treated as a name
                mojang_instance = GetMojangAPIData(search_term)
            else:
                mojang_instance = GetMojangAPIData(None, search_term)
            formated_username, uuid, has_cape, skin_id, cape_id, lookup_failed, cape_showcase_b64, cape_back_b64, cape_showcase, skin_showcase_b64 = mojang_instance.get_data()
            if not lookup_failed:
                logger.info(f"added cache for {formated_username}")
                status = "success"
                source = "mojang_api"
                self.cache_instance.add_mojang_cache(uuid, formated_username, has_cape, cape_id, skin_showcase_b64, cape_showcase_b64, cape_back_b64)
            else:
                logger.info(f"lookup failed for {search_term}, not adding to cache")
                status = "lookup_failed"
                source = "mojang_api"
        else:
            logger.info(f"using cache for {search_term}")
            data_from_cache = self.cache_instance.get_data_from_mojang_cache(search_term)
            try:
                uuid = data_from_cache["uuid"]
                formated_username = data_from_cache["username"]
                has_cape = data_from_cache["has_cape"]
                cape_id = data_from_cache["cape_name"]
                skin_showcase_b64 = data_from_cache["skin_showcase_b64"]
                cape_showcase_b64 = data_from_cache["cape_front_b64"]
                cape_back_b64 = data_from_cache["cape_back_b64"]
                status = "success"
                source = "cache"
            except KeyError as e:
                logger.error(f"KeyError while getting data from cache: {e}")
                status = "failed"
                source = "cache"
            logger.debug(f"data from cache: {data_from_cache}")
        

        response = {
            "status": status,
            "source": source,
            "uuid": uuid,
            "username": formated_username,
            "has_cape": bool(has_cape),
            "cape_name": cape_id,
            "skin_showcase_b64": skin_showcase_b64,
            "cape_showcase_b64": cape_showcase_b64,
            "cape_back_b64": cape_back_b64
        }

        return response

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    hypixel_api_key = os.getenv("HYPIXEL_API_KEY")
    data_manager = DataManager(hypixel_api_key)
    search_term = "miro407"
    response = data_manager.get_mojang_data(search_term)
    print(response)