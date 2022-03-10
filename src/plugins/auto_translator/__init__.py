# -*- coding: utf-8 -*-
import nonebot
from nonebot.matcher import Matcher
from nonebot import on_message, on_command
from nonebot.permission import USER, SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message

import asyncio
# Self-Utils
import src.plugins.auto_translator.db as db
import src.plugins.auto_translator.tmt as tmt
import src.plugins.auto_translator.tools as tools
# Initiate database
db.init()
USERS_ON = db.to_dict(asyncio.run(db.select()))
# HELP
helper = on_command(cmd="自动翻译帮助",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@helper.handle()
async def send_help(event:GroupMessageEvent):
    menu = '自动翻译模块目前支持的功能:\n\n'
    menu += '命令格式: "/自动翻译列表"\n'
    menu += '命令格式: "/开启自动翻译 QQ号 源语言->目标语言"\n'
    menu += '命令格式: "/关闭自动翻译 QQ号 [(optional)源语言->目标语言]"'
    await helper.send(menu)

# STATUS
status = on_command(cmd='自动翻译列表',temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@status.handle()
async def get_status(event:GroupMessageEvent):
    group_id = int(event.get_session_id().split('_')[1])
    user_list = await db.select(group_id=group_id)
    msg = "已开启以下群成员的自动翻译功能:\n"
    for i in range(len(user_list)):
        user_name = await tools.get_user_name(nonebot.get_bot(), group_id, user_list[i][2])
        msg += f"\n[{i + 1}] {user_name}({user_list[i][2]}): {user_list[i][3]}->{user_list[i][4]}"
    await status.send(msg)

# EVENT: add translate user
add = on_command(cmd='开启自动翻译',temp=False, priority=2, block=True,
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
        user_name = await tools.get_user_name(nonebot.get_bot(), group_id, user_id)
        if await db.insert(group_id, user_id, source, target):
            USERS_ON = db.to_dict(await db.select())
            translator.permission = USER(*USERS_ON.keys())
            msg = f"成功开启 {user_name}({user_id}): {source}->{target}"
        else:
            msg = f"{user_name}({user_id}): {source}->{target} 已经开启"
    else:
        msg = '命令格式错误，请严格按照\n"/开启自动翻译 QQ号 源语言->目标语言"\n的格式发送命令'
    await add.send(msg)

# EVENT: delete translate user
delete = on_command(cmd="关闭自动翻译",temp=False, priority=2, block=True,
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
        user_name = await tools.get_user_name(nonebot.get_bot(), group_id, user_id)
        if await db.delete(group_id, user_id, source, target):
            USERS_ON = db.to_dict(await db.select())
            translator.permission = USER(*USERS_ON.keys())
            if not source and not target:
                source = target = 'all'
            msg = f'成功关闭 {user_name}({user_id}): {source}->{target}'
        else:
            msg = f'{user_name}({user_id})的自动翻译功能未开启'
    else:
        msg = '命令格式错误，请严格按照\n"/关闭自动翻译 QQ号 [(optional)源语言->目标语言]"\n的格式发送命令'
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
    message_id = event.get_event_description().split()[1]
    message = event.get_message()
    fragments = tools.MessageFragments(message)
    for config in USERS_ON[session_id]:
        try:
            frag = fragments.copy()
            source, target = config['source'], config['target']
            target_texts = await tmt.translate(source, target, *frag.get_plain_text())
            frag.update_plain_text(target_texts)
            msg = frag.get_message()
            msg.insert(0, MessageSegment.text('【机翻】\r\n'))
            msg.insert(0, MessageSegment(
                type='reply', data={'id':message_id}
            ))
            await translator.send(msg)
        except Exception as err:
            await nonebot.get_bot().send_group_msg(
                group_id=nonebot.get_driver().config.dict()["admin_group"],
                message=f'发送{event.get_plaintext()}时:' + "\r\nError: " + str(err)
            )