# -*- coding: utf-8 -*-
# Python STL
import asyncio
# Third-party Library
import nonebot
from nonebot.plugin import require
from nonebot.log import logger
from nonebot import on_command, on_notice
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_OWNER, GROUP_ADMIN
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, GroupDecreaseNoticeEvent
# Self-tools
from . import db
from . import amzreq

# INITIATE DATABASE
db.init()

##########################
######### 包装函数 #########
async def send_msg_with_retry(bot, group_id:int, message:str):
    retry_time = 5
    send_success = False
    for i in range(retry_time):
        if send_success:
            break
        try:
            await bot.send_group_msg(
                group_id=group_id,
                message=message
            )
            send_success = True
        except:
            pass

def safe_get_bot():
    try:
        bot = nonebot.get_bot()
    except:
        bot = None

    return bot

########################
# HELP
helper = on_command(cmd="愿望单帮助", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
@helper.handle()
async def help_menu():
    menu = '愿望单模块目前支持的功能:\n'\
         + '(LID为愿望单URL中一串连续的数字+大写字母)\n\n'\
         + '命令格式: "/愿望单列表"\n'\
         + '命令格式: "/愿望单关注 对象名称 LID"\n'\
         + '命令格式: "/愿望单取关 对象名称"'
    await helper.finish(menu)

# STATUS
sub_status = on_command(cmd="愿望单列表", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
@sub_status.handle()
async def show_sub(event: GroupMessageEvent):  
    group_id = int(event.get_session_id().split('_')[1])
    sub_list = db.get_group_sub(group_id)
    if sub_list:
        msg = "本群已订阅以下对象愿望单: \n"
        i = 1
        for name in sub_list.values():
            msg += f"\n[{i}]{name}"
            i += 1
    else:
        msg = "本群还未订阅任何愿望单"
    await sub_status.finish(Message(msg))

# ADD subscribe
add = on_command(cmd="愿望单关注", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER)
@add.handle()
async def add_sub(event: GroupMessageEvent): 
    cmd =event.get_plaintext().split()
    msg = "命令错误, 请检查输入格式:\n/愿望单关注 对象名称 LID"
    if len(cmd) == 3:
        group_id = int(event.get_session_id().split('_')[1])
        name = cmd[1]
        lid = cmd[2]
        if 'WQJIE8LKY4EB' in lid:
            await add.finish("谁准你关注我的阿猪了？")
        if db.add_sub(lid, group_id, name):
            msg = f"{name}的愿望单订阅成功"   
        else:
            msg = f"{name}的愿望单订阅已存在"
    await add.finish(Message(msg))

# ADD subscribe (SUPERUSER ONLY)
add = on_command(cmd="愿望单关注",temp=False, priority=1, block=True,
    permission=SUPERUSER)
@add.handle()
async def add_listen(event:GroupMessageEvent):  
    cmd =event.get_plaintext().split()
    msg = "命令错误, 请检查输入格式:\n/愿望单关注 对象名称 LID"
    if len(cmd) == 3:
        group_id = int(event.get_session_id().split('_')[1])
        name = cmd[1]
        lid = cmd[2]
        if db.add_sub(lid, group_id, name):
            msg = f"{name}的愿望单订阅成功"   
        else:
            msg = f"{name}的愿望单订阅已存在"
    await add.finish(Message(msg))

# DELETE subscribe
delete = on_command(cmd="愿望单取关",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
@delete.handle()
async def delete_listen(event:GroupMessageEvent):
    cmd = event.get_plaintext().split()
    msg = "命令错误, 请检查输入格式:\n/愿望单取关 对象名称"
    if len(cmd) == 2:
        name = cmd[1]
        group_id = int(event.get_session_id().split('_')[1])
        sub_list = db.get_group_sub(group_id)
        for lid, sub_name in sub_list.items():
            if name == sub_name and db.delete_sub(lid, group_id):
                msg = f"{name}的愿望单订阅已成功取消"
                break
        else:
            msg = f"本群没有订阅{name}的愿望单"
    await delete.finish(Message(msg))

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
    id='wishlist_pusher', timezone='Asia/Shanghai')
@logger.catch
async def push_wishlist():
    bot = safe_get_bot()
    lid_list = db.get_user_list()
    url_list = amzreq.lid_to_url(*lid_list)
    text_list = await amzreq.request_many(*url_list)
    for i in range(len(text_list)):
        prev_items = db.get_items(lid_list[i])
        items = amzreq.find_all(text_list[i])
        if not items and not amzreq.is_clear(text_list[i]):
            items = prev_items
        buyed_items = amzreq.check_items(prev_items, items)
        new_items = amzreq.check_items(items, prev_items)
        db.update_items(lid_list[i], new_items, buyed_items)
        common_msg = amzreq.make_notice(new_items, buyed_items, url_list[i])
        groups = db.get_sub_group(lid_list[i])
        if common_msg:
            tasks = []
            for group_id, name in groups.items():
                group_msg = f'{name}的愿望单发生了变动'
                # 消息推送至Bark
                task = asyncio.create_task(
                    amzreq.push_to_bark(group_msg)
                )
                tasks.append(task)
                # 消息推送至群
                if bot is not None:
                    group_msg = group_msg + ":\n" + common_msg
                    task = asyncio.create_task(
                        send_msg_with_retry(bot, group_id, group_msg)
                    )
                    tasks.append(task)
                # 本地保存消息
                db.message_log(group_msg)
            await asyncio.gather(*tasks)