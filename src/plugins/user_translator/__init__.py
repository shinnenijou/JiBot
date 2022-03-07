# -*- coding: utf-8 -*-

import nonebot
from nonebot.matcher import Matcher
from nonebot import on_message, on_command
from nonebot.permission import USER, SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

import json
from os import mkdir
from sys import path
# Self-Utils
import tmt
import msg_tools
# load translate users config
try:
    mkdir("./data/user_translator")
except FileExistsError:
    pass
try:    
    with open("./data/user_translator/config.ini", "r") as file:
        TRANSLATE_USERS = json.loads(file.read())
except FileNotFoundError:
    TRANSLATE_USERS = {}
    with open("./data/user_translator/config.ini", "w") as file:
        file.write(json.dumps(TRANSLATE_USERS))

# HELP
helper = on_command(cmd="发言翻译帮助",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@helper.handle()
async def send_help():
    menu = '发言翻译模块目前支持的功能:\n\n'
    menu += '命令格式: "发言翻译列表"\n'
    menu += '命令格式: "开启发言翻译 QQ号 源语言->目标语言"\n'
    menu += '命令格式: "关闭发言翻译 QQ号"'
    await helper.finish(menu)

# STATUS
admin = on_command(cmd="发言翻译列表",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def del_user(event:GroupMessageEvent):
    group_id = event.get_session_id().partition('_')[1]
    msg = "以下成员的发言翻译功能正在运行: "
    for key, value in TRANSLATE_USERS.items():
        if group_id in key:
            msg += f"\r\nQQ{key.rpartition('_')[2]}: {value['source']}->{value['target']}"
    await admin.send(msg)

# EVENT: add translate user
admin = on_command(cmd="开启发言翻译",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def add_user(event:GroupMessageEvent):
    global TRANSLATE_USERS
    try:
        user_id = event.get_plaintext().split()[1]
        setting = event.get_plaintext().split()[2]
        source = setting.partition("->")[0]
        target = setting.partition("->")[2]
        isValidCmd = user_id.isdigit() and source and target
    except:
        isValidCmd = False
    if isValidCmd:
        session_id = f"{event.get_session_id().rpartition('_')[0]}_{user_id}"
        with open("./data/user_translator/config.ini", "r") as file:
            config = json.loads(file.read())
        if session_id not in config:
            config[session_id] = {"source":source, "target":target}
            file = open("./data/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            file.close()
            print(f"成功开启 QQ{user_id} 的发言翻译功能")
            #await admin.send(f"成功开启 QQ{user_id} 的发言翻译功能")
            TRANSLATE_USERS = config
            translator.permission = USER(*TRANSLATE_USERS.keys())
        else:
            await admin.send(f"QQ{user_id} 的发言翻译功能正在运行")

# EVENT: delete translate user
admin = on_command(cmd="关闭发言翻译",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def del_user(event:GroupMessageEvent):
    global TRANSLATE_USERS
    try:
        user_id = event.get_plaintext().split()[1]
        isValidCmd = user_id.isdigit()
    except:
        isValidCmd = False
    if isValidCmd:
        session_id = f"{event.get_session_id().rpartition('_')[0]}_{user_id}"
        with open("./data/user_translator/config.ini", "r") as file:
            config = json.loads(file.read())
        if session_id in config:
            del config[session_id]
            file = open("./data/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            await admin.send(f"成功关闭 QQ{user_id} 的发言翻译功能")
            file.close()
            TRANSLATE_USERS = config
            translator.permission = USER(*TRANSLATE_USERS.keys())
        else:
            await admin.send(f"QQ{user_id} 的发言翻译功能未开启")

# Event: translate for particular users
translator = on_message(temp=False, priority=5, block=True,
    permission=USER(*TRANSLATE_USERS.keys()))

@translator.permission_updater
async def update(matcher:Matcher):
    return matcher.permission

@translator.handle()
async def translate(event:GroupMessageEvent):
    if event.get_plaintext():
        msg = event.get_message()
        source_text = msg_tools.extract_nontext(msg)
        plain_text, emoji_list =  msg_tools.extract_emoji(source_text)        
        try:
            plain_text = tmt.translate(
                sourceText=plain_text,
                source=TRANSLATE_USERS[event.get_session_id()]["source"],
                target=TRANSLATE_USERS[event.get_session_id()]["target"]
                )
            target_text = msg_tools.recover_emoji(plain_text, emoji_list)
            msg = msg_tools.replace_plain_text(msg, target_text)
            msg.insert(0, MessageSegment(type='text', data={'text': '【机翻】'}))
            await translator.send(msg)
        except Exception as err:
            await nonebot.get_bot().send_group_msg(
                group_id=nonebot.get_driver().config.dict()["admin_group"],
                message=event.get_plaintext() + "\r\nError: " + str(err)
            )