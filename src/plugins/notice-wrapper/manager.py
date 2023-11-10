import os
from enum import IntEnum
import asyncio

from nonebot import logger
from nonebot.plugin import require

from .pushers import *


db = require("db-wrapper").db


class NoticeType(IntEnum):
    Bark = 1
    QQPrivate = 2
    QQGroup = 3


class NoticeManager:
    __PusherMap: dict[NoticeType, Pusher] = {
        NoticeType.Bark: BarkPusher(),
        NoticeType.QQPrivate: QQPrivatePusher(),
        NoticeType.QQGroup: QQGroupPusher(),
    }

    def __init__(self) -> None:
        self.__table_name = 'notice_info'
        self.__next_id = 1

        if not db.exists(self.__table_name):
            db.create(
                self.__table_name,
                'id',
                id='int',
                type='int',
                destination='varchar(255)'
            )

        result: list = db.select('id', self.__table_name)

        if len(result) > 0:
            result.sort(key=lambda x: x[0])
            self.__next_id = result[-1][0] + 1

    async def __push(self, _type: NoticeType, _content: any, _to: str) -> bool:
        if _type not in self.__PusherMap:
            logger.error('Pusher not found: type = ', _type)
            return False

        return await self.__PusherMap[_type].push(_content, _to)

    def register(self, _type: NoticeType, _to: str) -> int | None:
        if db.insert(self.__table_name, id=self.__next_id, type=_type, destination=_to):
            self.__next_id += 1
            return self.__next_id - 1

        return None

    def unregister(self, _id: int) -> None:
        db.delete(self.__table_name, id=_id)

    async def push(self, _content: any, _id: int) -> bool:
        result = db.select('type destination', self.__table_name, id=_id)

        if len(result) == 0:
            return False

        _type = result[0][0]
        _to = result[0][1]

        return await self.__push(_type, _content, _to)

    async def push_batch(self, _content: any, *_ids: int) -> None:
        tasks = []

        for _id in _ids:
            tasks.append(asyncio.create_task(self.push(_content, _id)))

        await asyncio.gather(*tasks)


pusher = NoticeManager()
