import requests
from nonebot.plugin import require
import nonebot
import json

########## Var #########
# 保存每个被监听的人的信息
# [NAME]{URL, GROUP_ID, PREV_LIST, CURR_LIST}
targets = {}
# 用于HTTP请求的请求头
HEADERS = {}
HEADERS["Host"] = "www.amazon.co.jp"
HEADERS["Accept"] = "text/html"
HEADERS["Accept-Language"] = "ja-JP"
HEADERS["Connection"] = "close"
########################

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

async def print_items(bot, items, str, name, group_id):
    if items:
        msg = f"{name}の欲しいものリストに以下の商品が{str}ました: \r\n"
        for item in items:
            msg += item + "\r\n"
        try:
            #print(msg)
            await bot.send_group_msg(group_id = group_id, message = msg)
        except:
            pass
 
def check_clear(string):
    # pattern found
    return string.find("このリストにはアイテムはありません") != -1

async def listen():
    bot = nonebot.get_bot()
    with open(f"./aji_bot/plugins/wishlist_listener/listen_list.json", "r") as file:
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
            await print_items(bot, new_items, "追加され", key, value["GROUP_ID"])
            await print_items(bot, buyed_items, "削除され", key, value["GROUP_ID"])
        except:
            pass

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(listen, "interval", minutes=10)