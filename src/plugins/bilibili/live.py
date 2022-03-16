# -*- coding: utf-8 -*-
# Python STL
from time import time, strftime, gmtime
import asyncio
# Third-party
import aiohttp
from bilibili_api import live, Credential
from bilibili_api.live import LiveRoom
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

##### OLD API
# async def get_live(session:aiohttp.ClientSession, uid:int) -> dict:
#     url = f'https://api.live.bilibili.com/room/v1/Room/get_info?room_id={uid}&from=room'
#     data = {}
#     try:
#         async with session.get(url) as resp:
#             data = await resp.json()
#             if data['code'] == 0:
#                 data = data['data']
#     except Exception as err:
#         logger.error(f'请求{uid}直播信息出现错误: str({err})')
#     return data

# async def get_live_list(*uids:int) -> list[dict]:
#     async with aiohttp.ClientSession() as session:
#         tasks = []
#         for uid in uids:
#             task = asyncio.create_task(get_live(session, uid))
#             tasks.append(task)
#         live_list = await asyncio.gather(*tasks)
#     return live_list

class LiveStatus():
    OFFLINE = 0
    LIVE = 1
    VIDEO = 2

class Room():

    def __init__(self, uid:int, room_id:int, name:str, credential:Credential):
        self.uid = uid
        self.room_id = room_id
        self.name = name
        self.live_status = LiveStatus.OFFLINE
        self.live_start_time = int(time())
        self.live_title = ""
        self.live_cover = ""
        self.room = LiveRoom(room_id, credential)
    
    async def update_live(self) -> bool:
        """
        更新直播状态, 返回状态是否有更新, 发生错误时不会被更新
        """
        is_updated = False
        try:
            play_info = await self.room.get_room_play_info()
            is_updated = play_info['live_status'] != self.live_status
            self.live_status = play_info['live_status']
            if self.live_status == LiveStatus.LIVE:  # 只在开播时更新直播开始时间
                self.live_start_time = int(play_info['live_time'])
        except Exception as err:
            logger.error(f'请求{self.room_id}直播信息时出现错误: {err}')
        return is_updated

    async def update_key_info(self) -> bool:
        """
        更新直播间关键信息, 包含标题, 封面url, 返回信息是否有更新, 发生错误时不会被更新
        """
        is_updated = False
        try:
            resp = await self.room.get_room_info()
            room_info = resp['room_info']
            is_updated = self.live_title != room_info['title']
            self.live_title = room_info['title']
            self.live_cover = room_info['cover']
        except Exception as err:
            logger.error(f'请求{self.room_id}直播信息时出现错误: {err}')
        return is_updated

    def get_message(self) -> bool:
        """
        构造用于发送qq信息的Message, 内容根据live_status生成
        WARNING: 原则上只能在更新直播状态发生变化以后调用
        """
        if self.live_status == LiveStatus.LIVE:
            msg = f'{self.name} 直播开始啦！\n'\
                + f'\n标题: {self.live_title}'\
                + f'\n开播时间: {strftime("%Y.%m.%d  %H:%M:%S", gmtime(self.live_start_time + 8 * 60 * 60))}'
            msg = Message(msg)
            msg.append(MessageSegment.image(self.live_cover))
            return msg
        else:
            duration = (int(time()) - self.live_start_time)/(60 * 60)
            msg = f'{self.name}({self.uid})结束直播\n本次直播时长:{duration:.1f}小时'
            return Message(msg)