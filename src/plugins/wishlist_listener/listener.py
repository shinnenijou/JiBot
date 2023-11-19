from enum import IntEnum

from nonebot import require


db_proxy = require("db").db_proxy
Subscription = require("db").AmazonListenTarget
Commodity = require("db").AmazonCommodity

pusher = require('notification').pusher

# for type check. DO NOT uncomment when commit
from src.plugins.db import AmazonListenTarget as Subscription, AmazonCommodity as Commodity, db_proxy, select
from src.plugins.notification import pusher, NoticeType


class UserType(IntEnum):
    Private = 1
    Group = 2

NoticeType

class Utils:

    @staticmethod
    def _query_sub(user_id: str):
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        return db_proxy.scalars(stmt).all()

    @staticmethod
    def query_sub(_user_id: str) -> str:
        result = Utils._query_sub(_user_id)

        if len(result) == 0:
            return "未订阅任何愿望单"

        msg = "本群已订阅以下对象:\n"
        msg = msg + '\n'.join(f'{target.name}: {target.dst}' for target in result)
        return msg

    @staticmethod
    def _subscribe(_type: UserType, _user_id: str, _name: str, _lid: str):

        pusher.register(NoticeType.)
        subscription = Subscription(type=_type, user_id=_user_id, name=_name, dst=_lid)


print(Utils.query_sub('test'))