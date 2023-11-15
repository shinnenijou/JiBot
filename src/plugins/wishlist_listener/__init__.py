"""
愿望单模块目前支持的功能:
(LID为愿望单URL中一串连续的数字+大写字母)
命令格式: "/愿望单列表
命令格式: "/愿望单关注 对象名称 LID
命令格式: "/愿望单取关 对象名称
"""

from nonebot import on_command, require
from nonebot.adapters.onebot.v12 import GroupMessageEvent, GROUP
from nonebot.plugin import PluginMetadata


pusher = require('notice-wrapper').pusher

__plugin_meta__ = PluginMetadata(
    name="AmazonWishlist",
    description="监听亚马逊愿望单更新状况, 有状态更新时向用户推送",
    usage=__doc__,
    type="application",
)

# HELP
helper = on_command(cmd='愿望单帮助', temp=False, priority=2, permission=GROUP)


@helper.handle()
async def help_menu(event: GroupMessageEvent):
    """命令格式: /愿望单帮助"""
    await helper.finish(__doc__)
