import asyncio
import aiohttp
import logging
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.Logger(__name__)

class OnlineStatus:
    def __init__(self, username, uuid, hypixel_api_key):
        self.username = username
        self.uuid = uuid
        self.hypixel_api_key = hypixel_api_key

    def start_requests(self) -> str:
        status = asyncio.run(self.requests_manager())
        print(status)
        return status
    
    async def requests_manager(self) -> str:
        """Fetches player status, requires uuid, username and hypixel api key
        returns a string"""
        async with aiohttp.ClientSession() as self.session:
            wynncraft_api_task = self.get_wynncraft_status()
            hypixel_api_task = self.get_hypixel_status()

            try:
                responses = await asyncio.gather(wynncraft_api_task, hypixel_api_task)
            except Exception as e:
                logger.warning(f"Something went wrong while fetching online status: {e}")
                return "offline"
            
            try:
                self.wynncraft_player_status = responses[0]["online"]
            except Exception as e:
                logger.warning(f"Something went wrong while fetching Wynncraft status {e}")
                self.wynncraft_player_status = False

            try:
                self.hypixel_player_status = responses[1]["session"]["online"]
            except Exception as e:
                logger.info(f"Something went wrong while fetching Hypixel status (this requires an API key) {e}")
                self.hypixel_player_status = False

            try:
                logger.info(f"Wynn Status: {self.wynncraft_player_status}")
                logger.info(f"Hypixel Status: {self.hypixel_player_status}")
            except:
                pass
            
            if self.wynncraft_player_status:
                return "Wynncraft"
            elif self.hypixel_player_status:
                return "Hypixel"
            else:
                return "offline"
    
    async def get_wynncraft_status(self):
        async with self.session.get(f"https://api.wynncraft.com/v3/player/{self.username}") as response:
            return await response.json()

    async def get_hypixel_status(self):
        if self.hypixel_api_key is not None and self.hypixel_api_key != "":
            async with self.session.get(url = "https://api.hypixel.net/v2/status", params = {"uuid": self.uuid}, headers = {"Api-Key": self.hypixel_api_key}) as response:
                return await response.json()

if __name__ == "__main__":
    user1 = OnlineStatus("GoSkyHigh", "3ff2e63ad63045e0b96f57cd0eae708d", os.getenv("hypixel_api_key"))
    user1.start_requests()