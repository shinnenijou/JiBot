# -*- coding: utf-8 -*-
from nonebot import on_command
from nonebot.permission import USER, SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent

helper = on_command(cmd="菜单", block=True, priority=1,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@helper.handle()
async def help_menu(event:GroupMessageEvent):
    menu = "欢迎使用JiBot鸡器人! 阿鸡爱你哦😘\n现支持以下模块:\n\n"\
         + '【愿望单监听推送】发送 "/愿望单帮助" 获取命令帮助\n'\
         + '【自动翻译】发送 "/自动翻译帮助" 获取命令帮助\n'\
         + '【文本翻译】发送 "/翻译帮助" 获取命令帮助\n'\
         + '【推特监听推送】发送 "/推特帮助" 获取命令帮助\n'\
         + '【bilibili监听推送】发送 "/bili帮助" 获取命令帮助\n'\
         + '【工作表】发送 "/工作表帮助" 获取命令帮助'
    await helper.finish(menu)
    