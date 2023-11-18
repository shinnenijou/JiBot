from enum import IntEnum
import asyncio

from nonebot.plugin import require

from .pushers import *


db_proxy = require("db").db_proxy
Data = require("db").NoticeMethod

# for type check. DO NOT uncomment when commit
# from src.plugins.db import NoticeMethod as Data, db_proxy


class NoticeType(IntEnum):
    DebugLog = 0
    Bark = 1
    QQPrivate = 2
    QQGroup = 3


class NoticeManager:
    __PusherMap: dict[NoticeType, Pusher] = {
        NoticeType.DebugLog: DebugLogPusher(),
        NoticeType.Bark: BarkPusher(),
        NoticeType.QQPrivate: QQPrivatePusher(),
        NoticeType.QQGroup: QQGroupPusher(),
    }

    async def __push(self, _type: NoticeType, _content: any, _to: str) -> bool:
        if _type not in self.__PusherMap:
            logger.error('Pusher not found: type = ', _type)
            return False

        return await self.__PusherMap[_type].push(_content, _to)

    @staticmethod
    def register(_type: NoticeType, _to: str) -> int:
        new_data = Data(type=_type, dst=_to)
        db_proxy.add(new_data)
        db_proxy.flush()

        return new_data.id

    @staticmethod
    def unregister(_id: int) -> None:
        data = db_proxy.get(Data, _id)

        if data is not None:
            db_proxy.delete(data)

    async def push(self, _content: any, _id: int) -> bool:
        data = db_proxy.get(Data, _id)

        if data is None:
            return False

        _type = data.type
        _to = data.dst

        return await self.__push(_type, _content, _to)

    async def push_batch(self, _content: any, *_ids: int) -> None:
        tasks = []

        for _id in _ids:
            tasks.append(asyncio.create_task(self.push(_content, _id)))

        await asyncio.gather(*tasks)


pusher = NoticeManager()
