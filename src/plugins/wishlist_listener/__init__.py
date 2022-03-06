from tokenize import group
import nonebot
from nonebot.plugin import require
from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_OWNER, GROUP_ADMIN, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent

import requests
import json
from os import mkdir

########## Var #########
# 保存每个被监听的人的信息
# [NAME]{URL, GROUP_ID, PREV_LIST, CURR_LIST}
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
targets = {}
# 用于HTTP请求的请求头
HEADERS = {}
HEADERS["Host"] = "www.amazon.co.jp"
HEADERS["Accept"] = "text/html"
HEADERS["Accept-Language"] = "ja-JP"
HEADERS["Connection"] = "close"
########################
admin = on_command(cmd="愿望单列表", temp=False, priority=1, block=True,
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

add = on_command(cmd="愿望单关注",temp=False, priority=1, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@add.handle()
async def add_target(event:GroupMessageEvent):
    cmd = event.get_plaintext().split()
    if len(cmd) == 3:
        name = cmd[1]
        url = cmd[2]
        group_id = int(event.get_session_id().rpartition('_')[0][6:])
        with open(f"./data/wishlist_listener/config.ini", "r") as file:
            config = json.loads(file.read())
        if name not in config:
            config[name] = {"URL":url, "GROUP_ID":[group_id]}
            await add.send("添加成功")
        elif group_id not in config[name]["GROUP_ID"]:
            config[name]["GROUP_ID"].append(group_id)
            await add.send("添加成功")
        else:
            await add.send("已存在")
        with open(f"./data/wishlist_listener/config.ini", "w") as file:
                file.write(json.dumps(config))

delete = on_command(cmd="愿望单取关",temp=False, priority=1, block=True,
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

def request(url, headers):
    try:
        # 向amazon请求网页html
        response = requests.get(url, headers=headers)
        response.encoding = "UTF-8"
        resp = response.text
    except:
        # 发生任何异常都跳出
        resp = ""
    return resp
def find_item(string, begin):
    item_beg = string.find("itemName", begin, len(string))
    if item_beg == -1:
        item_title = ""
        title_end = -1
    else:
        title_beg = string.find("title", item_beg, len(string))
        title_end = string.find("href", title_beg, len(string))
        item_title = string[title_beg + 7: title_end - 2].strip()
    return item_title, title_end
def find_items(string):
    temp_list = []
    if string:
        # 如果get没有发生异常，则对返回的html进行处理
        begin = 0
        # 将返回数据中包含的愿望单物品全部添加至列表中
        while begin != -1:
            # 查找愿望单中是否有物品
            item_title, begin = find_item(string, begin)
            if item_title:
                temp_list.append(item_title)
    return temp_list
def check_items(list1, list2):
    # 比对两个列表，找出list1中不在list2中的元素
    not_include = []
    for item in list1:
        if item not in list2:
            not_include.append(item)
    return not_include
async def print_items(bot, items, str, name, url, groups):
    if items:
        msg = f"{name}のほしい物リストに以下の商品が{str}ました: \r\n"
        for item in items:
            msg += item + "\r\n"
        msg += url
        try:
            #print(msg)
            for group_id in groups:
                await bot.send_group_msg(group_id = group_id, message = msg)
        except:
            pass
def check_clear(string):
    # pattern found
    return string.find("このリストにはアイテムはありません") != -1
async def listen():
    global targets
    bot = nonebot.get_bot()
    with open(f"./data/wishlist_listener/config.ini", "r") as file:
        targets_config = json.loads(file.read())
        # 删除不在监听列表中的目标
        for key, value in targets.items():
            if key not in targets_config:
                del targets[key]
        # 增加新增的目标
        for key, value in targets_config.items():
            if key not in targets:
                targets[key] = value
                targets[key]["PREV_LISTS"] = []
                targets[key]["CURR_LISTS"] = []
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

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(listen, "interval",
    minutes=int(nonebot.get_driver().config.dict()['wishlist_listen_interval']))