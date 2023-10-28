import os
import json

from nonebot import logger, get_driver

# Initialize
TEMP_DIR = os.path.join(get_driver().config.dict()[
                        'data_path'], 'recorder', 'temp')

if not os.path.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)


def listen_twicast(id: str) -> dict:
    API = f"https://twitcasting.tv/streamserver.php?target={id}&mode=client"

    resp_file = os.path.join(TEMP_DIR, f'{id}_resp.json')

    if os.system(f'curl -s -o "{resp_file}" "{API}"') != 0:
        logger.error(f"[Recorder]Requests Response Error: {API}")
        return False
    
    with open(resp_file, 'r', encoding='utf-8') as file:
        text = file.read() 
    
    os.remove(resp_file)

    try:
        live_info = json.loads(text)
    except Exception as e:
        logger.error(
            "[Recorder]Responce format error. Not a valid json format. ")
        return False

    ret = {}

    ret['Result'] = live_info.get('movie', {}).get('live', 0) == 1
    ret['Title'] = ''

    return ret  


def listen_bilibili(id: str) -> dict:
    API = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={id}&from=room"

    resp_file = os.path.join(TEMP_DIR, f'{id}_resp.json')

    if os.system(f'curl -s -o "{resp_file}" "{API}"') != 0:
        logger.error(f"[Recorder]Requests Response Error: {API}")
        return False

    with open(resp_file, 'r', encoding='utf-8') as file:
        text = file.read()

    os.remove(resp_file)

    try:
        live_info = json.loads(text)
    except Exception as e:
        logger.error(
            "[Recorder]Responce format error. Not a valid json format. ")
        return False

    ret = {}

    ret['Result'] = live_info.get('data', {}).get('live_status', 0) == 1
    ret['Title'] = live_info.get('data', {}).get('title', '').replace(' ', '_')

    return ret

SUPPORT_PLATFORM = {
    'twicast': listen_twicast,
    'bilibili': listen_bilibili,
}

def listen(platform: str, id: str) -> bool:
    if not SUPPORT_PLATFORM.get(platform.lower(), False):
        logger.error(f"[Recorder]Platform not supported: {platform}.")
        return

    return SUPPORT_PLATFORM[platform](id)
