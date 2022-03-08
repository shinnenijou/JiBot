# -*- coding: utf-8 -*-
# Python STL
import requests
import json
from os import mkdir
import sys
# Third-party Library
import nonebot
from nonebot.plugin import require
from nonebot import on_command, on_notice
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_OWNER, GROUP_ADMIN, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GroupDecreaseNoticeEvent

########## Var #########
# 保存每个被监听的人的信息
# {NAME:{URL, GROUP_ID, PREV_LIST, CURR_LIST}}
try:
    mkdir("./data/wishlist_listener")
except FileExistsError:
    pass
try:
    with open(f"./data/wishlist_listener/config.ini", "x") as file:
        file.write("{}")
        pass
except:
    pass

# 用于HTTP请求的请求头
HEADERS = {}
HEADERS["Host"] = "www.amazon.co.jp"
HEADERS["Accept"] = "text/html"
HEADERS["Accept-Language"] = "ja-JP"
HEADERS["Connection"] = "close"
########################
# HELP
helper = on_command(cmd="愿望单帮助", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@helper.handle()
async def help_menu():
    menu = '愿望单模块目前支持的功能:\n\n'
    menu += '命令格式: "愿望单列表"\n'
    menu += '命令格式: "愿望单关注 名称 URL"\n'
    menu += '命令格式: "愿望单取关 名称"'
    await helper.finish(menu)

# STATUS
admin = on_command(cmd="愿望单列表", temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def print_targets(event:GroupMessageEvent):
    group_id = int(event.get_session_id().rpartition('_')[0][6:])
    with open(f"./data/wishlist_listener/config.ini", "r") as file:
        config = json.loads(file.read())
    msg = "已开启以下对象愿望的监听: "
    for name, info in config.items():
        if group_id in info["GROUP_ID"]:
            msg += f"\r\n{name}"
    await admin.send(msg)

# ADD
add = on_command(cmd="愿望单关注",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@add.handle()
async def add_target(event:GroupMessageEvent):
    cmd = event.get_plaintext().split()
    if len(cmd) == 3:
        name = cmd[1]
        url = cmd[2]
        group_id = int(event.get_session_id().split('_')[2])
        with open(f"./data/wishlist_listener/config.ini", "r") as file:
            config = json.loads(file.read())
        if name not in config:
            config[name] = {
                "URL":url,
                "GROUP_ID":[group_id],
                "CURR_LISTS":[],
                "PREV_LISTS":[]
            }
            await add.send("添加成功")
        elif group_id not in config[name]["GROUP_ID"]:
            config[name]["GROUP_ID"].append(group_id)
            await add.send("添加成功")
        else:
            await add.send("已存在")
        with open(f"./data/wishlist_listener/config.ini", "w") as file:
                file.write(json.dumps(config))

# DELETE
delete = on_command(cmd="愿望单取关",temp=False, priority=2, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@delete.handle()
async def add_target(event:GroupMessageEvent):
    cmd = event.get_plaintext().split()
    if len(cmd) == 2:
        name = cmd[1]
        group_id = int(event.get_session_id().rpartition('_')[0][6:])
        with open(f"./data/wishlist_listener/config.ini", "r") as file:
            config = json.loads(file.read())
        if name in config and group_id in config[name]["GROUP_ID"]:
            config[name]["GROUP_ID"].remove(group_id)
            await delete.send("已删除")
            if not config[name]["GROUP_ID"]:
                del config[name]
        else:
            await delete.send("未找到")
        with open(f"./data/wishlist_listener/config.ini", "w") as file:
            file.write(json.dumps(config))

# DELETE after quit from group
group_decrease = on_notice(priority=1, block=False)
@group_decrease.handle()
async def _(event: GroupDecreaseNoticeEvent):
    group_id = event.get_session_id().split('_')[1]
    if event.self_id == event.user_id:
        with open(f"./data/wishlist_listener/config.ini", "r") as file:
            config = json.loads(file.read())
        for name, data in config.items():
            if group_id in data['GROUP_ID']:
                data['GROUP_ID'].remove(group_id)
            if not data['GROUP_ID']:
                del config[name]
        with open(f"./data/wishlist_listener/config.ini", "w") as file:
            file.write(config)


async def listen():
    bot = nonebot.get_bot()
    with open(f"./data/wishlist_listener/config.ini", "r") as file:
        targets = json.loads(file.read())
    for key, value in targets.items():
        try:
            text = request(value["URL"], HEADERS)
            targets[key]["CURR_LISTS"] = find_items(text)
            # 如果愿望单突然完全清空，则检查文本中是否确实包含无物品信息
            if not targets[key]["CURR_LISTS"] and not check_clear(text):
                targets[key]["CURR_LISTS"] = targets[key]["PREV_LISTS"]
            new_items = check_items(targets[key]["CURR_LISTS"], targets[key]["PREV_LISTS"])
            buyed_items = check_items(targets[key]["PREV_LISTS"], targets[key]["CURR_LISTS"])
            targets[key]["PREV_LISTS"] = targets[key]["CURR_LISTS"]
            await print_items(bot, new_items, "追加され", key, value["URL"], value["GROUP_ID"])
            await print_items(bot, buyed_items, "削除され", key, value["URL"], value["GROUP_ID"])
        except:
            pass
        targets[key]['CURR_LISTS'] = []
    with open(f"./data/wishlist_listener/config.ini", "w") as file:
        file.write(json.dumps(targets))

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(listen, "interval",
    seconds=int(nonebot.get_driver().config.dict()['wishlist_listen_interval']))