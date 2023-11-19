import aiohttp

from nonebot import logger

from src.plugins.db import db_proxy
from src.plugins.db import select
from src.plugins.db import AmazonListenTarget as Subscription, AmazonCommodity as Commodity
from src.plugins.notification import NoticeType, pusher


class Listener:
    __NoticeMap = {
        'debug': NoticeType.DebugLog,
        'bark': NoticeType.Bark,
        'private': NoticeType.QQPrivate,
        'group': NoticeType.QQGroup
    }

    def __init__(self):
        self.__http_session: aiohttp.ClientSession | None = None
        self.__db_session = db_proxy

    def select_subs(self, _user_id: str):
        stmt = select(Subscription).where(Subscription.user_id == _user_id)
        return self.__db_session.scalars(stmt).all()

    def select_targets(self):
        stmt = select(Subscription).distinct(Subscription.target)
        return self.__db_session.scalars(stmt).all()

    def select_notices(self, _lid: str):
        stmt = select(Subscription).where(Subscription.target == _lid).distinct(Subscription.notice_id)
        return self.__db_session.scalars(stmt).all()

    def query_sub(self, _user_id: str) -> str:
        result = self.select_subs(_user_id)

        if len(result) == 0:
            return "未订阅任何愿望单"

        msg = "本群已订阅以下对象:\n"
        msg = msg + '\n'.join(f'{target.name}: {target.dst}' for target in result)
        return msg

    def _subscribe(self, _user_id: str, _name: str, _lid: str, _notice_type: int, _push_to: str):
        notice_id = pusher.register(_notice_type, _push_to)
        subscription = Subscription(user_id=_user_id, name=_name, target=_lid, notice_id=notice_id)
        self.__db_session.add(subscription)

    def subscribe(self, _user_id: str, _name: str, _lid: str, _notice_type: str, _push_to: str) -> str:
        if _notice_type not in self.__NoticeMap:
            return f'不支持的推送方式: {_notice_type}'

        _notice_type = self.__NoticeMap.get(_notice_type)

        self._subscribe(_user_id, _name, _lid, _notice_type, _push_to)

        return '订阅成功'

    def unsubscribe_by_name(self, _name: str) -> bool:
        stmt = select(Subscription).where(Subscription.name == _name)
        result = self.__db_session.scalars(stmt).all()

        if len(result) == 0:
            return False

        for subscription in self.__db_session.scalars(stmt).all():
            self.__db_session.delete(subscription)

        return True

    def unsubscribe_by_lid(self, _lid: str) -> bool:
        stmt = select(Subscription).where(Subscription.target == _lid)
        result = self.__db_session.scalars(stmt).all()

        if len(result) == 0:
            return False

        for subscription in result:
            self.__db_session.delete(subscription)

        return True

    @staticmethod
    def _build_url(_lid: str):
        return f'https://www.amazon.co.jp/hz/wishlist/ls/{_lid}'

    async def request(self, _lid: str) -> tuple[str, str]:
        if self.__http_session is None:
            self.__http_session = aiohttp.ClientSession(
                headers={
                    "Host": "www.amazon.co.jp",
                    "Accept": "text/html",
                    "Accept-Language": "ja-JP",
                    "Connection": "close"
                }
            )
        try:
            async with self.__http_session.get(self._build_url(_lid)) as resp:
                text = await resp.text()
        except Exception as e:
            logger.error(e)
            text = ''

        return _lid, text

    def add_commodity(self, _lid: str, _name: str, add_time: int):
        commodity = Commodity(lid=_lid, name=_name, addTime=add_time, deleteTime=0)
        self.__db_session.add(commodity)

    @staticmethod
    def _find(string: str, sub_string: str, start: int = 0):
        """
        包装str.find函数, 查找失败时返回尾后索引而非-1
        """
        index = string.find(sub_string, start)

        if index == -1:
            return len(string)

        return index

    @staticmethod
    def parse_resp(text: str) -> set[str] | None:
        """
        解析html页面文本, 提取出包含的商品title.
        请求错误产生的空字符串将会返回None与没有商品区分
        """
        commodities = set()

        # 需要区分请求错误和确实不包含商品, 请求错误时返回None
        if text == '':
            return None

        # 没有商品时返回空列表
        if Listener._find(text, "このリストにはアイテムはありません") != len(text):
            return commodities

        # 商品名是个标准的<a>标签, 找到包含id为itemName的a标签html内容既为商品标题
        index = Listener._find(text, 'itemName')

        while index != len(text):
            begin = Listener._find(text, '>', index)

            if begin == len(text):
                break

            end = Listener._find(text, '</a>', begin)

            if end == len(text):
                break

            name = text[begin + 1: end]

            commodities.add(name)

            index = Listener._find(text, 'itemName', end)

        return commodities

    @staticmethod
    def build_message(_add_items: set[str], _delete_items: set[str], _lid: str):
        """
        通过给定的add_items和delete_items构造通知信息, 如果两个items都是空则返回空的字符串
        """
        msg = ""

        if _add_items:
            msg += "--------------------\n"
            msg += f"以下の商品が追加されました:\n"
            index = 1
            for item in _add_items:
                msg += f'[{index}]{item}\n'
                index += 1

        if _delete_items:
            msg += "--------------------\n"
            msg += f"以下の商品が削除されました:\n"
            index = 1
            for item in _delete_items:
                msg += f'[{index}]{item}\n'
                index += 1

        if msg:
            msg += "--------------------\n"
            msg += Listener._build_url(_lid)

        return msg

    def delete_commodity(self, _lid: str, _name: str, delete_time: int):
        stmt = select(Commodity).where(Commodity.lid).where(Commodity.name == _name).where(Commodity.deleteTime == 0)
        for commodity in self.__db_session.scalars(stmt).all():
            commodity.deleteTime = delete_time

    def select_commodities(self, _lid: str):
        stmt = select(Commodity).where(Commodity.lid == _lid).where(Commodity.deleteTime == 0)
        return self.__db_session.scalars(stmt).all()


listener = Listener()
