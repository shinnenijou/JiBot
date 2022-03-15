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
UID_LIST, ROOM_LIST, NAME_LIST, NEWEST_DYNAMICS = db.get_user_list()
for i in range(len(ROOM_LIST)):  # Initialize Room list
    ROOM_LIST[i] = Room(UID_LIST[i], ROOM_LIST[i], NAME_LIST[i], CREDENTIAL)
TRANSLATOR_LIST = db.get_translator_list()[0]
DYNAMIC_QUEUE = deque()
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
@scheduler.scheduled_job('interval', seconds=DYNAMIC_LISTEN_INTERVAL, id='dynamic')
async def push_dynamic():
    global DYNAMIC_QUEUE, NEWEST_DYNAMICS
    # 清理超时动态队列, pop掉发布时间戳离当前时间超过COMMENT_EXPIRATION的动态
    while len(DYNAMIC_QUEUE):
        front = DYNAMIC_QUEUE.popleft()
        if time() - front.timestamp < COMMENT_EXPIRATION:
            DYNAMIC_QUEUE.appendleft(front)
            break

    if not UID_LIST:
        return  # 监听名单里没有目标
    bot = nonebot.get_bot()
    timeline_list = await dynamics.get_users_timeline(CREDENTIAL, *UID_LIST)
    # 每个用户的最新动态分别处理
    # 索引i: 指示第几个用户
    for i in range(len(timeline_list)):
        # 读取订阅该用户的群
        group_list, translate_list = db.get_user_groups(UID_LIST[i])
        # 从旧到新倒着扫描
        # 索引j: 该用户的第j条动态
        for j in range(len(timeline_list[i]) - 1, -1 , -1):
            dynamic_info = timeline_list[i][j]
            # 该动态时间戳比记录的要早则跳过
            if dynamic_info['desc']['timestamp'] <= NEWEST_DYNAMICS[i]:
                continue
            logger.success(f'成功检测到{UID_LIST}发布新动态, 准备推送')
            dynamic = dynamics.CLASS_MAP[dynamic_info['desc']['type']](dynamic_info, CREDENTIAL)
            # 翻译该动态
            await dynamic.translate(BILI_SOURCE, BILI_TARGET)
            # 推送至群
            # 索引k: 指示订阅该用户的群
            tasks = []
            for k in range(len(group_list)):
                message = dynamic.make_message(translate_list[k])
                task = asyncio.create_task(
                    bot.send_group_msg(
                        group_id=group_list[k],
                        message=message
                    )
                )
                tasks.append(task)
            try:
                await asyncio.gather(*tasks)
            except:
                logger.error(f'发送{UID_LIST[i]}群消息失败, 请检查网络连接或qq账号状态')
            # 保存该动态至内存, 供回复使用
            DYNAMIC_QUEUE.append(dynamic)
        # 更新时间戳, 返回动态从新到旧, 直接取第一条更新
        NEWEST_DYNAMICS[i] = timeline_list[i][0]['desc']['timestamp']
        db.update_timestamp(UID_LIST[i], NEWEST_DYNAMICS[i])

###########################
######### 直播推送 #########
@scheduler.scheduled_job('interval', seconds=LIVE_LISTEN_INTERVAL, id='live')
async def push_live():
    global ROOM_LIST
    bot = nonebot.get_bot()
    tasks = []
    for room in ROOM_LIST:
        tasks.append(asyncio.create_task(room.update_live()))
    updates = await asyncio.gather(*tasks)
    for i in range(len(updates)):
        # 直播状态有更新(包括开播与下播)，准备推送通知
        if updates[i]:
            logger.success(f'成功检测到{NAME_LIST[i]}({UID_LIST[i]})直播状态变化, 准备推送')
            await ROOM_LIST[i].update_key_info()
            message = ROOM_LIST[i].make_message()
            group_list = db.get_user_groups(UID_LIST[i])[0]
            tasks = []
            for group_id in group_list:
                task = asyncio.create_task(
                    bot.send_group_msg(
                        group_id=group_id,
                        message=message
                    )
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

###########################
######### 发送评论 #########
send_comment = on_command(cmd='评论', priority=2, temp=False, block=True,
    permission=USER(*TRANSLATOR_LIST))
@send_comment.handle()
async def send(event:GroupMessageEvent):
    args = event.get_plaintext().partition(' ')[2]
    dynamic_id = args.split()[0]
    msg = '命令格式错误, 请按照命令格式: "/评论 动态id 评论内容"'
    if not dynamic_id.isdigit():
        return
    text = args[len(dynamic_id):].strip()
    dynamic_id = int(dynamic_id)
    for dynamic in DYNAMIC_QUEUE:
        if dynamic.dynamic_id == dynamic_id:
            try:
                await comment.send_comment(
                    text=text,
                    oid=dynamic.reply_id,
                    type_=dynamics.REPLY_MAP[dynamic.type],
                    credential=CREDENTIAL
                )
                msg = '评论发送成功'
            except:
                logger.error('发送评论失败, 请检查网络状况或Bili账号配置')
            break
    else:
        msg = '发送失败, 请检查动态id'
    await send_comment.finish(Message(msg))

###########################
######### 订阅管理 #########
# 显示本群中的关注列表 
userlist = on_command(cmd='bili关注列表', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@userlist.handle()
async def get_list(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    msg = '本群已关注以下用户:\n'
    uid_list, name_list, translate_list = db.get_group_sub(group_id)
    for i in range(len(name_list)):
        translate_text = '开启' if translate_list[i] else '关闭'
        msg += f'\n[{i + 1}]{name_list[i]}({uid_list[i]}) 翻译已{translate_text}'
    await userlist.finish(Message(msg))

# 关注用户
follow_user = on_command(cmd='bili关注', priority=2, temp=False, block=True,
    permission=GROUP_OWNER|GROUP_ADMIN|SUPERUSER)
@follow_user.handle()
async def follow(event:GroupMessageEvent):
    global UID_LIST, NAME_LIST, NEWEST_DYNAMICS, ROOM_LIST

    cmd = event.get_plaintext().split()
    group_id = event.get_session_id().split('_')[1]
    msg = '命令格式错误, 请按照命令格式: "/bili关注 数字uid"'
    if len(cmd) != 2 or not cmd[1].isdigit():
        await follow_user.finish(Message(msg))
    uid = int(cmd[1])
    user_info = (await users.get_users_info(CREDENTIAL, uid))[0]
    if user_info:
        name = user_info['name']
        room_id = 0
        if user_info['live_room']:
            room_id = user_info['live_room']['roomid']
        if db.add_user(uid, room_id, name, int(time())):  # 最新动态时间戳设置为当前时间
            # 更新全局变量
            UID_LIST.append(uid)
            NAME_LIST.append(name)
            NEWEST_DYNAMICS.append(int(time()))
            ROOM_LIST.append(Room(uid, room_id, name, CREDENTIAL))
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
    global UID_LIST, NAME_LIST, NEWEST_DYNAMICS
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/bili取关 数字uid"'
    if len(cmd) == 2 and cmd[1].isdigit():
        uid = int(cmd[1])
        name = db.get_user_name(uid)
        if db.delete_group_sub(uid, group_id):
            msg = f"{name}({uid})取关成功"
            # 更新全局变量
            UID_LIST, _, NAME_LIST, NEWEST_DYNAMICS = db.get_user_list()
            if len(NAME_LIST) < len(ROOM_LIST):
                for room in ROOM_LIST:
                    if room.uid == uid:
                        ROOM_LIST.remove(room)
                        break
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
    session_id_list, name_list = db.get_translator_list()
    msg = '以下用户已加入评论白名单:\n'
    for i in range(len(session_id_list)):
        group_id = session_id_list[i].split('_')[1]
        qq_id = session_id_list[i].split('_')[2]
        qq_name = name_list[i]
        msg += f'\n[{i + 1}]群{group_id}: {qq_name}({qq_id})'
    print(msg)
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
            TRANSLATOR_LIST, _ = db.get_translator_list()
            send_comment.permission = USER(*TRANSLATOR_LIST)
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
            TRANSLATOR_LIST, _ = db.get_translator_list()
            send_comment.permission = USER(*TRANSLATOR_LIST)
        else:
            msg = '查无此人, 请确认群号 QQ号无误'
    await remove_translator.finish(Message(msg))

