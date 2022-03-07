# -*- coding: utf-8 -*-
import nonebot
from nonebot.matcher import Matcher
from nonebot import on_message, on_command
from nonebot.permission import USER, SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message

import asyncio
# Self-Utils
import src.plugins.user_translator.db as db
import src.utils.tmt as tmt
import src.utils.msg_tools as msg_tools
# Initiate database
db.init()
USERS_ON = db.to_dict(asyncio.run(db.select()))
# HELP
helper = on_command(cmd="发言翻译帮助",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@helper.handle()
async def send_help(event:GroupMessageEvent):
    menu = '发言翻译模块目前支持的功能:\n\n'
    menu += '命令格式: "发言翻译列表"\n'
    menu += '命令格式: "开启发言翻译 QQ号 源语言->目标语言"\n'
    menu += '命令格式: "关闭发言翻译 QQ号 [(optional)源语言->目标语言]"'
    await helper.send(menu)

# STATUS
status = on_command(cmd='发言翻译列表',temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@status.handle()
async def get_status(event:GroupMessageEvent):
    group_id = int(event.get_session_id().split('_')[1])
    user_list = await db.select(group_id=group_id)
    msg = "已开启以下群成员的发言翻译功能:\n"
    for i in range(len(user_list)):
        msg += f"\n[{i + 1}] {user_list[i][2]}: {user_list[i][3]}->{user_list[i][4]}"
    print(USERS_ON)
    await status.send(msg)

# EVENT: add translate user
add = on_command(cmd='开启发言翻译',temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@add.handle()
async def add_user(event:GroupMessageEvent):
    global translator
    global USERS_ON
    try:
        group_id = int(event.get_session_id().split('_')[1])
        user_id = int(event.get_plaintext().split()[1])
        setting = event.get_plaintext().split()[2].split('->')
        source = setting[0]
        target = setting[1]
        isValidCmd = True
    except FileNotFoundError:
        isValidCmd = False
    if isValidCmd:
        if await db.insert(group_id, user_id, source, target):
            USERS_ON = db.to_dict(await db.select())
            translator.permission = USER(*USERS_ON.keys())
            msg = f"成功开启 QQ{user_id}: {source}->{target} 的发言翻译功能"
        else:
            msg = f"QQ{user_id}: {source}->{target} 的发言翻译功能已经开启"
    else:
        msg = '命令格式错误，请严格按照\n"/开启发言翻译 QQ号 源语言->目标语言"\n的格式发送命令'
    await add.send(msg)

# EVENT: delete translate user
delete = on_command(cmd="关闭发言翻译",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@delete.handle()
async def del_user(event:GroupMessageEvent):
    global translator
    global USERS_ON
    try:
        group_id = int(event.get_session_id().split('_')[1])
        user_id = int(event.get_plaintext().split()[1])
        isValidCmd = True
    except:
        isValidCmd = False
    try:
        setting = event.get_plaintext().split()[2].split('->')
        source = setting[0]
        target = setting[1]
    except:
        source = None
        target = None
    if isValidCmd:
        if await db.delete(group_id, user_id, source, target):
            USERS_ON = db.to_dict(await db.select())
            translator.permission = USER(*USERS_ON.keys())
            msg = f'成功关闭 QQ{user_id}: {source}->{target} 的发言翻译功能'
        else:
            msg = f'QQ{user_id}: {source}->{target} 的发言翻译功能未开启'
    else:
        msg = '命令格式错误，请严格按照\n"/开启发言翻译 QQ号 [(optional)源语言->目标语言]"\n的格式发送命令'
    await delete.send(msg)

# Event: translate for particular users
translator = on_message(temp=False, priority=5, block=True,
    permission=USER(*USERS_ON.keys()))

@translator.permission_updater
async def update(matcher:Matcher):
    return matcher.permission

@translator.handle()
async def translate(event:GroupMessageEvent):
    if not event.get_plaintext():
        return None
    session_id = event.get_session_id()
    messages = [[] for i in range(len(USERS_ON[session_id]))]
    try:
        for seg in event.get_message():
            if seg['type'] == 'text':
                text_list, emoji_list = msg_tools.split_emoji(seg['data']['text'])
                for i in range(len(USERS_ON[session_id])):
                    messages[i].append(
                        MessageSegment.text(
                            msg_tools.recover_emoji(
                                await tmt.translate_list(
                                    text_list,
                                    USERS_ON[session_id][i]['source'],
                                    USERS_ON[session_id][i]['target']
                                ),
                                emoji_list
                            )
                        )
                    )
            elif seg['type'] in msg_tools.PLAIN_TEXT:
                messages[i].append(seg)
        for i in range(len(USERS_ON[session_id])):
            messages[i].insert(0, MessageSegment.text('【机翻】'))
            await translator.send(messages[i])
    except Exception as err:
        await nonebot.get_bot().send_group_msg(
            group_id=nonebot.get_driver().config.dict()["admin_group"],
            message=f'发送{event.get_plaintext()}时:' + "\r\nError: " + str(err)
        )