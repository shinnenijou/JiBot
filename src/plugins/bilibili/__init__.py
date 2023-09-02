# -*- coding: utf-8 -*-
# Python STL
from time import time, sleep
import asyncio
from collections import deque
# Third-party
from bilibili_api import Credential, comment
import nonebot
from nonebot.log import logger
from nonebot import on_command, require
from nonebot.permission import SUPERUSER, USER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
# Self
import src.plugins.bilibili.dynamics as dynamics
import src.plugins.bilibili.db as db
import src.plugins.bilibili.users as users
from src.plugins.bilibili.live import LiveStatus, Room
# Initiate Database
db.init()
# Credential
SESSDATA = nonebot.get_driver().config.dict()['bili_sessdata']
BILI_JCT = nonebot.get_driver().config.dict()['bili_jct']
BUVID3 = nonebot.get_driver().config.dict()['bili_buvid3']
CREDENTIAL = Credential(SESSDATA, BILI_JCT, BUVID3)
# CONSTANT
BILI_SOURCE = nonebot.get_driver().config.dict()['bili_source']
BILI_TARGET = nonebot.get_driver().config.dict()['bili_target']
DYNAMIC_LISTEN_INTERVAL = nonebot.get_driver().config.dict()['dynamic_listen_interval']
LIVE_LISTEN_INTERVAL = nonebot.get_driver().config.dict()['live_listen_interval']
COMMENT_EXPIRATION = nonebot.get_driver().config.dict()['dynamic_comment_expiration']
# GLOBAL VIRIABLES
#UID_LIST, ROOM_LIST, NAME_LIST, NEWEST_DYNAMICS = db.get_user_list()
USER_LIST = db.get_user_list()
for uid, info in USER_LIST.items():  # Initialize Room list
    info['room'] = Room(uid, info['room'], info['name'], CREDENTIAL)
TRANSLATOR_LIST = db.get_translator_list()
DYNAMIC_QUEUE = deque()

##########################
######### 包装函数 #########
async def send_msg_with_retry(bot, group_id:int, message:str):
    retry_time = 1
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


##########################
######### 命令帮助 #########
helper = on_command(cmd='bili帮助', priority=2, temp=False, block=True, 
    permission=GROUP_OWNER|GROUP_ADMIN|SUPERUSER)
@helper.handle() 
async def help():
    menu = 'bilibili模块目前支持的功能:\n\n'\
         + '/bili关注列表\n'\
         + '/bili关注 ID\n'\
         + '/bili取关 ID\n'\
         + '/开启动态翻译 ID\n'\
         + '/关闭动态翻译 ID\n'\
         + '/评论白名单\n'\
         + '/添加评论白名单 ID\n'\
         + '/移除评论百名单 ID'
    await helper.finish(Message(menu))

# 定时任务对象
scheduler = require('nonebot_plugin_apscheduler').scheduler

###########################
######### 动态推送 #########
@scheduler.scheduled_job('interval', seconds=DYNAMIC_LISTEN_INTERVAL,
    id='bili_dynamic_pusher', timezone='Asia/Shanghai')
@logger.catch
async def push_dynamic():
    global USER_LIST
    # 清理超时动态队列, pop掉发布时间戳离当前时间超过COMMENT_EXPIRATION的动态
    while len(DYNAMIC_QUEUE):
        front = DYNAMIC_QUEUE.popleft()
        if time() - front.timestamp < COMMENT_EXPIRATION:
            DYNAMIC_QUEUE.appendleft(front)
            break

    if not USER_LIST:
        return  # 监听名单里没有目标
    bot = nonebot.get_bot()
    timelines = await dynamics.get_users_timeline(CREDENTIAL, *USER_LIST.keys())
    # 每个用户的最新动态分别处理
    # 索引i: 指示第几个用户
    for uid, timeline in timelines.items():
        # 读取订阅该用户的群
        groups = db.get_user_groups(uid)
        # 从旧到新倒着扫描
        # 索引j: 该用户的第j条动态
        for dynamic_data in reversed(timeline):
            # 该动态时间戳比记录的要早则跳过
            if dynamic_data['desc']['timestamp'] <= USER_LIST[uid]['newest_timestamp']:
                continue
            logger.success(f'成功检测到{USER_LIST[uid]["name"]}发布新动态, 准备推送')
            # 示例化为动态类
            dynamic = dynamics.CLASS_MAP[dynamic_data['desc']['type']](dynamic_data, CREDENTIAL)
            await dynamic.translate(BILI_SOURCE, BILI_TARGET)
            # 推送至群
            # 索引k: 指示订阅该用户的群
            tasks = []
            for group_id, need_transtale in groups.items():
                message = dynamic.get_message(need_transtale)
                task = asyncio.create_task(
                    send_msg_with_retry(bot, group_id, message)
                )
                tasks.append(task)
            # 发送成功后更新内存中的时间戳
            USER_LIST[uid]['newest_timestamp'] = dynamic_data['desc']['timestamp']
            # 保存该动态至内存, 供回复使用
            DYNAMIC_QUEUE.append(dynamic)
            # 先更新后发送防止反复重试
            await asyncio.gather(*tasks)
        # 更新时间戳至数据库
        db.update_timestamp(uid, USER_LIST[uid]['newest_timestamp'])

###########################
######### 直播推送 #########
@scheduler.scheduled_job('interval', seconds=LIVE_LISTEN_INTERVAL,
    id='bili_live_pusher', timezone='Asia/Shanghai')
@logger.catch
async def push_live():
    global USER_LIST
    if not USER_LIST:
        return
    bot = nonebot.get_bot()
    tasks = []
    for info in USER_LIST.values():
        tasks.append(asyncio.create_task(info['room'].update_live()))
    updates = dict(zip(USER_LIST.keys(), await asyncio.gather(*tasks)))
    for uid, update in updates.items():
        # 直播状态有更新(包括开播与下播)，准备推送通知
        if update:
            logger.success(f'成功检测到{USER_LIST[uid]["name"]}({uid})直播状态变化, 准备推送')
            await USER_LIST[uid]['room'].update_key_info()
            message = USER_LIST[uid]['room'].get_message()
            groups = db.get_user_groups(uid)
            tasks = []
            for group_id in groups.keys():
                task = asyncio.create_task(
                    send_msg_with_retry(bot, group_id, message)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

###########################
######### 订阅管理 #########
# 显示本群中的关注列表 
userlist = on_command(cmd='bili关注列表', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@userlist.handle()
async def get_list(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    msg = '本群已关注以下用户:\n'
    group_sub = db.get_group_sub(group_id)
    i = 0
    for uid, info in group_sub.items():
        i = i + 1
        translate_text = '开启' if info.get('need_translate', False) else '关闭'
        msg += f'\n[{i}]{info.get("name", uid)}({uid}) 翻译已{translate_text}'
    await userlist.finish(Message(msg))

# 关注用户
follow_user = on_command(cmd='bili关注', priority=2, temp=False, block=True,
    permission=GROUP_OWNER|GROUP_ADMIN|SUPERUSER)
@follow_user.handle()
async def follow(event:GroupMessageEvent):
    global USER_LIST

    cmd = event.get_plaintext().split()
    group_id = event.get_session_id().split('_')[1]
    msg = '命令格式错误, 请按照命令格式: "/bili关注 数字uid"'
    if len(cmd) != 2 or not cmd[1].isdigit():
        await follow_user.finish(Message(msg))
    uid = cmd[1]
    user_info = (await users.get_users_info(CREDENTIAL, uid))[0]
    if user_info:
        name = user_info['name']
        room_id = 0
        if user_info['live_room']:
            room_id = user_info['live_room']['roomid']
        if db.add_user(uid, room_id, name, int(time())):  # 最新动态时间戳设置为当前时间
            # 更新全局变量
            USER_LIST[uid] = {
                'name': name,
                'room': Room(uid, room_id, name, CREDENTIAL),
                'newest_timestamp': int(time())
            }
        if db.add_group_sub(uid, group_id):
            msg = f'{name}({uid}) 关注成功！'
        else:
            msg = f'{name}({uid})已经在关注列表中！'
    else:
        msg = f'用户{uid}不存在, 请确认id无误'
    await follow_user.finish(Message(msg))

#取关用户  
unfollow_user = on_command('bili取关', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@unfollow_user.handle()
async def unfollow(event:GroupMessageEvent):
    global USER_LIST
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/bili取关 数字uid"'
    if len(cmd) == 2 and cmd[1].isdigit():
        uid = cmd[1]
        name = db.get_user_name(uid)
        if db.delete_group_sub(uid, group_id):
            msg = f"{name}({uid})取关成功"
            # 更新全局变量
            if db.delete_user(uid):
                del USER_LIST[uid]
        else:
            msg = f"{uid}不在本群关注列表中"
    await unfollow_user.finish(Message(msg))

#开启动态翻译
translate_on = on_command('开启动态翻译', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@translate_on.handle()
async def on(event: GroupMessageEvent):
    group_id = int(event.get_session_id().split('_')[1])
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/开启动态翻译 数字uid"'
    if len(cmd) == 2 and cmd[1].isdigit():
        uid = int(cmd[1])
        name = db.get_user_name(uid)
        if db.translate_on(uid, group_id):
            msg = f'{name}({uid})开启动态翻译成功！'
        else:
            msg = f'{uid}不在当前关注列表！'
    await translate_on.finish(Message(msg))

#关闭动态翻译
translate_off = on_command('关闭动态翻译', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@translate_off.handle()
async def off(event: GroupMessageEvent):
    group_id = int(event.get_session_id().split('_')[1])
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/开启动态翻译 数字uid"'
    if len(cmd) == 2 and cmd[1].isdigit():
        uid = int(cmd[1])
        name = db.get_user_name(uid)
        if db.translate_off(uid, group_id):
            msg = f'{name}({uid})关闭动态翻译成功！'
        else:
            msg = f'{uid}不在当前关注列表！'
    await translate_off.finish(Message(msg))

###########################
######### 评论管理 #########
# 查看评论白名单
show_translator = on_command(cmd='评论白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@show_translator.handle()
async def show():
    msg = '以下用户已加入评论白名单:\n'
    i = 0
    for session_id, name in TRANSLATOR_LIST.items():
        i += 1
        group_id = session_id.split('_')[1]
        qq_id = session_id.split('_')[2]
        msg += f'\n[{i}]群{group_id}: {name}({qq_id})'
    await show_translator.finish(Message(msg))

# 添加评论白名单
add_translator = on_command(cmd='添加评论白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@add_translator.handle()
async def add(event:GroupMessageEvent):
    global TRANSLATOR_LIST
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/添加评论白名单 群号 qqid"'
    if len(cmd) == 3 and cmd[1].isdigit() and cmd[2].isdigit():
        group_id = int(cmd[1])
        qq_id = int(cmd[2])
        try:
            qq_user_info = await nonebot.get_bot().get_group_member_info(
                group_id=group_id, user_id=qq_id, nocache=False
            )
            qq_name = qq_user_info['card'] if qq_user_info['card'] else qq_user_info['nickname']
        except:
            qq_user_info = {}
        if qq_user_info and db.add_translator_list(qq_id, group_id, qq_name):
            msg = f'群{group_id}: {qq_name}({qq_id})添加成功'
            TRANSLATOR_LIST = db.get_translator_list()
            send_comment.permission = USER(*TRANSLATOR_LIST.keys())
        else:
            msg = '查无此人, 请确认群号 QQ号无误'
    await add_translator.finish(Message(msg))

# 移除评论白名单
remove_translator = on_command(cmd='移除评论白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@remove_translator.handle()
async def remove(event:GroupMessageEvent):
    global TRANSLATOR_LIST
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/移除评论白名单 群号 qq号"'
    if len(cmd) == 3 and cmd[1].isdigit() and cmd[2].isdigit():
        group_id = int(cmd[1])
        qq_id = int(cmd[2])
        try:
            qq_user_info = await nonebot.get_bot().get_group_member_info(
                group_id=group_id, user_id=qq_id, nocache=False
            )
            qq_name = qq_user_info['card'] if qq_user_info['card'] else qq_user_info['nickname']
        except:
            qq_user_info = {}
        if qq_user_info and db.remove_translator_list(qq_id, group_id):
            msg = f'群{group_id}: {qq_name}({qq_id})移除成功'
            TRANSLATOR_LIST = db.get_translator_list()
            send_comment.permission = USER(*TRANSLATOR_LIST.keys())
        else:
            msg = '查无此人, 请确认群号 QQ号无误'
    await remove_translator.finish(Message(msg))

