from enum import IntEnum

from nonebot import require

db_proxy = require("db").db_proxy
Subscription = require("db").AmazonListenTarget
Commodity = require("db").AmazonCommodity

pusher = require('notification').pusher

# for type check. DO NOT uncomment when commit
from src.plugins.db import AmazonListenTarget as Subscription, AmazonCommodity as Commodity, db_proxy, select
from src.plugins.notification import pusher, NoticeType


class Utils:
    __NoticeMap = {
        'debug': NoticeType.DebugLog,
        'bark': NoticeType.Bark,
        'private': NoticeType.QQPrivate,
        'group': NoticeType.QQGroup
    }

    @staticmethod
    def select_subs(_user_id: str):
        stmt = select(Subscription).where(Subscription.user_id == _user_id)
        return db_proxy.scalars(stmt).all()

    @staticmethod
    def select_targets():
        stmt = select(Subscription).distinct(Subscription.target)
        return db_proxy.scalars(stmt).all()

    @staticmethod
    def select_notices(_lid: str):
        stmt = select(Subscription).where(Subscription.target == _lid)
        return db_proxy.scalars(stmt).all()

    @staticmethod
    def query_sub(_user_id: str) -> str:
        result = Utils.select_subs(_user_id)

        if len(result) == 0:
            return "未订阅任何愿望单"

        msg = "本群已订阅以下对象:\n"
        msg = msg + '\n'.join(f'{target.name}: {target.dst}' for target in result)
        return msg

    @staticmethod
    def _subscribe(_user_id: str, _name: str, _lid: str, _notice_type: int, _push_to: str):
        notice_id = pusher.register(_notice_type, _push_to)
        subscription = Subscription(user_id=_user_id, name=_name, target=_lid, notice_id=notice_id)
        db_proxy.add(subscription)

    @staticmethod
    def subscribe(_user_id: str, _name: str, _lid: str, _notice_type: str, _push_to: str) -> str:
        if _notice_type not in Utils.__NoticeMap:
            return f'不支持的推送方式: {_notice_type}'

        _notice_type = Utils.__NoticeMap.get(_notice_type)

        Utils._subscribe(_user_id, _name, _lid, _notice_type, _push_to)

        return '订阅成功'

    @staticmethod
    def unsubscribe_by_name(_name: str) -> bool:
        stmt = select(Subscription).where(Subscription.name == _name)
        result = db_proxy.scalars(stmt).all()

        if len(result) == 0:
            return False

        for subscription in db_proxy.scalars(stmt).all():
            db_proxy.delete(subscription)

        return True

    @staticmethod
    def unsubscribe_by_lid(_lid: str) -> bool:
        stmt = select(Subscription).where(Subscription.target == _lid)
        result = db_proxy.scalars(stmt).all()

        if len(result) == 0:
            return False

        for subscription in result:
            db_proxy.delete(subscription)

        return True

    @staticmethod
    async def request(_lid: str) -> tuple[str, str]:
        assert False
        return _lid, ''
