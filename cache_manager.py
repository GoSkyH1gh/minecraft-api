import sqlite3
import logging
from pathlib import Path
import time

logger = logging.getLogger(__file__)

current_directory = Path(__file__).parent

class CacheManager:
    def __init__(self):
        self.conn = sqlite3.Connection(current_directory / "storage" / "cache.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mojang_cache (
            uuid TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            has_cape BOOLEAN NOT NULL,
            cape_name TEXT,
            skin_showcase_b64 TEXT,
            cape_front_b64 TEXT,
            cape_back_b64 TEXT,
            timestamp INTEGER NOT NULL)
        """)

        #self.cursor.execute("""
        #CREATE TABLE IF NOT EXISTS hypixel_cache (
        #    uuid TEXT PRIMARY KEY,
        #    first_login TEXT,
        #    rank TEXT,
        #    guild_name TEXT
        #""")

    def check_mojang_cache(self, search_term: str, time_between_cache: int = 360):
        results = self.cursor.execute("SELECT timestamp FROM mojang_cache WHERE uuid = ? OR LOWER(username) = ?", (search_term.lower(), search_term.lower(),)).fetchall()
        try:
            last_timestamp = results[0][0]
            print(last_timestamp)
            if self.is_cache_valid(last_timestamp, time_between_cache):
                logger.info(f"Cache found for UUID: {search_term}, returning True")
                return True
            else:
                logger.info(f"Cache expired for UUID: {search_term}, returning False")
                return False
        except IndexError:
            logger.info(f"No cache found for UUID: {search_term}")
            return False
        
    
    def get_data_from_mojang_cache(self, search_term: str):
        """Retrieve Mojang cache data for a given UUID or username."""
        
        self.cursor.execute("SELECT * FROM mojang_cache WHERE uuid = ? OR LOWER(username) = ?", (search_term.lower(), search_term.lower(),))
        results = self.cursor.fetchone()
        
        if results:
            logger.info(f"Cache found for search term: {search_term}")
            return {
                "uuid": results[0],
                "username": results[1],
                "has_cape": results[2],
                "cape_name": results[3],
                "skin_showcase_b64": results[4],
                "cape_front_b64": results[5],
                "cape_back_b64": results[6],
                "timestamp": results[7]
            }
        else:
            logger.info(f"No cache found for UUID: {search_term}")
            return None

    def add_mojang_cache(
            self, uuid: str, username: str, has_cape: bool = False, cape_name: str = None,
            skin_showcase_b64: str = None, cape_front_b64: str = None, cape_back_b64: str = None
            ):
        """Add or update Mojang cache data for a given UUID."""

        self.cursor.execute(
            """INSERT OR REPLACE INTO mojang_cache (uuid, username, has_cape, cape_name, skin_showcase_b64, cape_front_b64, cape_back_b64, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))""", (uuid, username, has_cape, cape_name, skin_showcase_b64, cape_front_b64, cape_back_b64))
        self.conn.commit()
    
    def add_hypixel_cache(self, uuid: str, hypixel_data: str):
        conn = sqlite3.Connection(current_directory / "storage" / "cache.db")

        cursor = conn.cursor()
    
    def is_cache_valid(self, timestamp, threshold):
        return time.time() - timestamp < threshold


if __name__ == "__main__":
    cache_instance = CacheManager()
    #cache_instance.add_mojang_cache("3ff2e63ad63045e0b96f57cd0eae708d", "GoSkyHigh", True, "Purple Heart", "base64yap", None, None)
    #results = cache_instance.cursor.execute("SELECT * FROM mojang_cache").fetchall()
    #cache_instance.cursor.execute("DROP TABLE mojang_cache")
    print(f"finished")
    