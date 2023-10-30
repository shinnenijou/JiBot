import os
from datetime import datetime
import pytz
import asyncio

import nonebot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, GroupIncreaseNoticeEvent, MessageSegment
from nonebot.log import logger


class Singleton:
    __instance = None

    def __new__(cls, *argv, **kwarg):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance


def Mkdir(path: str):
    "Create a directary if not exists"
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


def Touch(path: str, orig_text: str = "") -> bool:
    "Create a new file if not exists"
    try:
        file = open(path, 'r')
        file.close()
    except FileNotFoundError:
        file = open(path, 'w')
        file.write(orig_text)
        file.close()


def get_group_id(event: GroupMessageEvent) -> str:
    return str(event.get_session_id().split('_')[1])


def get_cmd_param(event: GroupMessageEvent) -> list[str]:
    return event.get_plaintext().strip().split()[1:]


def get_cmd(event: GroupMessageEvent) -> str:
    return event.get_plaintext().strip().split()[0]


def safe_get_bot():
    try:
        bot = nonebot.get_bot()
    except Exception as e:
        logger.error(f"get bot error: {str(e)}")
        bot = None

    return bot

async def get_qq_name(group_id, user_id) -> str:
    bot = safe_get_bot()

    if bot is None:
        return "774"

    user_info = await bot.get_group_member_info(
        group_id=group_id, user_id=user_id, nocache=False
    )
    user_name = user_info['nickname']
    if user_info['card']:
        user_name = user_info['card']
    return user_name

def get_datetime(timezone: str = "Asia/Shanghai") -> str:
    tz = pytz.timezone(timezone)
    dt_now = datetime.now(tz)
    return dt_now.strftime("%Y%m%d_%H%M%S")

def parse_datetime(timestr: str, timezone: str = "Asia/Shanghai") -> int:
    tz = pytz.timezone(timezone)

    try:
        dt = datetime.strptime(timestr, "%Y%m%d_%H%M%S").astimezone(tz)
    except ValueError:
        return 0

    return int(dt.timestamp())

async def send_to_admin(message: str):
    bot = safe_get_bot()

    if bot is None:
        return

    admin_group = nonebot.get_driver().config.dict().get('admin_group', '')

    if not admin_group:
        return

    try:
        await bot.send_group_msg(
            group_id=admin_group,
            message=message
        )
    except Exception as e:
        logger.error(f"Send message error: {str(e)}")