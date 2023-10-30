import os
import json
import aiohttp

from nonebot import logger, get_driver

# Initialize
TEMP_DIR = os.path.join(get_driver().config.dict()['data_path'], 'recorder', 'temp')

class Listener:
    def __init__(self) -> None:
        self.__handlers = {
            'twicast': self.__listen_twicast,
            'bilibili': self.__listen_bilibili,
        }

        self.__session = None

    async def __aiohttp_get(self, url: str):
        if self.__session is None:
            self.__session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))

        text = ""

        try:
            async with self.__session.get(url) as resp:
                text = await resp.text()
        except Exception as e:
            logger.error(f"Request Error: {str(e)}")

        return text

    @staticmethod
    def __curl_get(url: str):
        resp_file = os.path.join(TEMP_DIR, f'{id}_resp.json')
        text = ""

        if os.system(f'curl -s -o "{resp_file}" "{url}"') != 0:
            logger.error(f"Requests Response Error: {url}")
            return text
        
        with open(resp_file, 'r', encoding='utf-8') as file:
            text = file.read() 
        
        os.remove(resp_file)

        return text

    async def __listen_twicast(self, id: str) -> dict:
        ret = {}

        API = f"https://twitcasting.tv/streamserver.php?target={id}&mode=client"
        text = await self.__aiohttp_get(API)        

        try:
            live_info = json.loads(text)
        except Exception as e:
            logger.error("Responce Not a valid json format.")
            ret['Result'] = False
            return ret

        ret['Result'] = live_info.get('movie', {}).get('live', 0) == 1
        ret['Title'] = ''

        return ret  

    async def __listen_bilibili(self, id: str) -> dict:
        ret = {}

        API = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={id}&from=room"
        text = await self.__aiohttp_get(API)

        try:
            live_info = json.loads(text)
        except Exception as e:
            logger.error(
                "Responce format error. Not a valid json format. ")
            ret['Result'] = False
            return ret

        ret['Result'] = live_info.get('data', {}).get('live_status', 0) == 1
        ret['Title'] = live_info.get('data', {}).get('title', '').replace(' ', '_')

        return ret

    async def listen(self, platform: str, id: str) -> bool:
        if not self.__handlers.get(platform.lower(), False):
            logger.error(f"Platform not supported: {platform}.")
            return

        return await self.__handlers[platform](id)

listener = Listener()
