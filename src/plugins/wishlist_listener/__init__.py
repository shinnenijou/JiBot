"""
愿望单模块目前支持的功能:
(LID为愿望单URL中一串连续的数字+大写字母)
命令格式: "/愿望单列表
命令格式: "/愿望单关注 对象名称 LID
命令格式: "/愿望单取关 对象名称
"""

import asyncio

from nonebot import on_command, require, get_driver
from nonebot.adapters.onebot.v12 import MessageEvent, PrivateMessageEvent, GroupMessageEvent, GROUP, PRIVATE
from nonebot.plugin import PluginMetadata

ascheduler = require()

# __init__ -> listener  -> db
from .listener import Utils

pusher = require('notification').pusher

__plugin_meta__ = PluginMetadata(
    name="AmazonWishlist",
    description="监听亚马逊愿望单更新状况, 有状态更新时向用户推送",
    usage=__doc__,
    type="application",
)

# HELP
matcher = on_command(cmd='愿望单帮助', priority=2, permission=GROUP | PRIVATE)


@matcher.handle()
async def help_menu(event: GroupMessageEvent):
    """命令格式: 愿望单帮助"""
    await matcher.finish(__doc__)


# Group Subscribe
matcher = on_command(cmd='愿望单关注', force_whitespace=True, priority=2, permission=GROUP)


@matcher.handle()
async def subscribe(event: GroupMessageEvent):
    """
    命令格式: 愿望单关注 名称 LID [推送途径 推送目的地]
    """

    params = event.get_plaintext().split()

    if len(params) < 3:
        matcher.finish(subscribe.__doc__.strip())

    name = params[1]
    lid = params[2]
    notice_type = 'group'
    push_to = event.group_id

    if len(params) >= 5:
        notice_type = params[3]
        push_to = params[4]

    matcher.finish(Utils.subscribe(
        _user_id=event.group_id,
        _name=name,
        _lid=lid,
        _notice_type=notice_type,
        _push_to=push_to,
    ))


# Unsubscribe
matcher = on_command(cmd='愿望单关注', force_whitespace=True, priority=2, permission=GROUP)


@matcher.handle()
async def unsubscribe(event: GroupMessageEvent):
    """
    命令格式: 愿望单取关 名称|LID
    """

    params = event.get_plaintext().split()

    if len(params) < 2:
        matcher.finish(unsubscribe.__doc__.strip())

    if Utils.unsubscribe_by_lid(params[1]):
        matcher.finish('取关成功')

    if Utils.unsubscribe_by_name(params[1]):
        matcher.finish('取关成功')

    matcher.finish('没有找到对应订阅')


# Query
matcher = on_command(cmd='愿望单关注名单', priority=2, permission=GROUP)


@matcher.handle()
async def query_sub(event: GroupMessageEvent):
    matcher.finish(Utils.query_sub(event.group_id))


# Listen
scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job(
    trigger='interval',
    seconds=int(get_driver().config.dict().get('wishlist_listen_interval', 300)),
    id=__plugin_meta__.name, timezone='Asia/Shanghai')
async def try_listen():
    subscriptions = Utils.select_targets()

    tasks = []

    for subscription in subscriptions:
        asyncio.create_task(Utils.request(subscription.target))

    resp = await asyncio.gather(*tasks)

