# -*- coding: utf-8 -*-
# Python STL
import asyncio
# Third-party Library
import nonebot
from nonebot.plugin import require
from nonebot.log import logger
from nonebot import on_command, on_notice
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_OWNER, GROUP_ADMIN, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, GroupDecreaseNoticeEvent
# Self-tools
import src.plugins.wishlist_listener.db as db
import src.plugins.wishlist_listener.utils as utils

# INITIATE DATABASE
db.init()

########################
# HELP
helper = on_command(cmd="愿望单帮助", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@helper.handle()
async def help_menu():
    menu = '愿望单模块目前支持的功能:\n\n'
    menu += '命令格式: "/愿望单列表"\n'
    menu += '命令格式: "/愿望单关注 名称 URL"\n'
    menu += '命令格式: "/愿望单取关 名称"'
    await helper.finish(menu)

# STATUS
admin = on_command(cmd="愿望单列表", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def print_targets(event : GroupMessageEvent):  
    group_id = int(event.get_session_id().split('_')[1])
    listen_list = db.get_users_on(group_id)
    msg = "已开启以下对象愿望的监听: \r\n"
    for name in listen_list:
        msg += f"\r\n{name}"
    await admin.send(msg)

# ADD a listen target
add = on_command(cmd="愿望单关注",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@add.handle()
async def add_listen(event:GroupMessageEvent): 
    cmd =event.get_plaintext().split()
    if len(cmd) == 3:
        name = cmd[1]
        url = cmd[2]
        if 'WQJIE8LKY4EB' in url:
            await add.finish("谁准你关注阿猪了？")
        group_id = int(event.get_session_id().split('_')[1])
        listen_list = db.get_users_on(group_id)
        if name not in listen_list:
            db.add_listen(group_id, name, url)
            await add.send("添加成功")       
        else:
            await add.send("已存在")
    else:
        await add.send("命令错误, 请检查输入格式: \r\n/愿望单关注 名称 URL")

# ADD a listen target(SUPERUSER ONLY)
add = on_command(cmd="愿望单关注",temp=False, priority=1, block=True,
    permission=SUPERUSER)
@add.handle()
async def add_listen(event:GroupMessageEvent):  
    cmd =event.get_plaintext().split()
    if len(cmd) == 3:
        name = cmd[1]
        url = cmd[2]
        group_id = int(event.get_session_id().split('_')[1])
        listen_list = db.get_users_on(group_id)
        if name not in listen_list:
            db.add_listen(group_id, name, url) 
            await add.send("添加成功")          
        else:
            await add.send("已存在")
    else:
        await add.send("命令错误, 请检查输入格式: \r\n/愿望单关注 名称 URL")

# DELETE a listen target
delete = on_command(cmd="愿望单取关",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@delete.handle()
async def delete_listen(event:GroupMessageEvent):
    cmd = event.get_plaintext().split()
    if len(cmd) == 2:
        name = cmd[1]
        group_id = int(event.get_session_id().split('_')[1])
        listen_list = db.get_users_on(group_id)
        if name in listen_list:
            logger.success('删除成功')
            db.delete_listen(group_id, name)
            await delete.send("已删除")
        else:
            await delete.send("未找到")
    else:
        await delete.send("命令错误, 请检查输入格式:\r\n/愿望单取关 名称")

# DELETE after quit from group
group_decrease = on_notice(temp=False, priority=2, block=False)
@group_decrease.handle()
async def _(event: GroupDecreaseNoticeEvent):
    group_id = event.get_session_id().split('_')[1]
    if event.self_id == event.user_id:
        db.delete_group(group_id)

# Listen
scheduler = require("nonebot_plugin_apscheduler").scheduler
@scheduler.scheduled_job(
    trigger='interval',
    seconds=nonebot.get_driver().config.dict()['wishlist_listen_interval'],
    id='wishlist')
async def push_wishlist():
    bot = nonebot.get_bot()
    target_list = db.get_all_users()
    url_list = [db.get_url(target) for target in target_list]
    text_list = await utils.request_many(*url_list)
    for i in range(len(text_list)):
        prev_items = db.get_items(target_list[i])
        items = utils.find_all(text_list[1])
        if not items and not utils.check_clear(text_list[i]):
            items = prev_items
        buyed_items = utils.check_items(prev_items, items)
        new_items = utils.check_items(items, prev_items)
        db.update_commodities(target_list[i], new_items, buyed_items)
        msg = utils.make_notice(new_items, buyed_items, target_list[i], url_list[i])
        group_list = db.get_groups_on(target_list[i])
        if msg:
            logger.success(f'检测到{target_list[i]}愿望单添加了新商品, 准备推送')
            tasks = []
            for group_id in group_list:
                tasks.append(
                    bot.send_group_msg(
                        group_id=group_id,
                        message=msg
                    )
                )
            await asyncio.gather(*tasks)