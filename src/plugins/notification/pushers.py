from abc import ABC, abstractmethod

import aiohttp
from nonebot import logger, get_bot, get_bots
from nonebot.adapters.onebot.v12.message import Message, MessageSegment


class Pusher(ABC):

    @abstractmethod
    async def push(self, _message: any, _to: str) -> bool:
        pass


class DebugLogPusher(Pusher):

    async def push(self, _message: str, _to: str) -> bool:
        logger.debug(_message)
        return True


class BarkPusher(Pusher):
    def __init__(self) -> None:
        super().__init__()
        self.__session = None

    async def push(self, _message: str, _to: str) -> bool:
        if self.__session is None:
            self.__session = aiohttp.ClientSession()

        if not _to:
            return False

        if _to[-1] != '/':
            _to += '/'

        _to = _to + _message

        try:
            async with self.__session.get(_to) as resp:
                await resp.start()
                status = resp.status

            return status == 200
        except Exception as e:
            logger.error(str(e))
            return False


class QQPusher(Pusher):
    async def call_api(self, api: str, **kwargs) -> bool:
        if len(get_bots()) == 0:
            return False

        bot = get_bot()

        try:
            await bot.call_api(api, **kwargs)
            return True
        except Exception as e:
            logger.error(str(e))
            return False


class QQPrivatePusher(QQPusher):
    async def push(self, _message: str | Message | MessageSegment, _to: str) -> bool:
        await self.call_api('send_private_msg', user_id=_to, message=_message)


class QQGroupPusher(QQPusher):
    async def push(self, _message: str | Message | MessageSegment, _to: str) -> bool:
        await self.call_api('send_group_msg', group_id=_to, message=_message)
