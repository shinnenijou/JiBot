import requests
import nonebot
from nonebot.plugin import require

########## URL #########
# 乙女音
#name = "乙女音"
#URL = "https://www.amazon.co.jp/hz/wishlist/ls/1JL7SPMBV2XB2?ref_=wl_fv_le"
# 咪太君
name = "mitagun"
URL = "https://www.amazon.co.jp/gp/aw/ls/ref=aw_wl_lol_wl?ie=UTF8&lid=WQJIE8LKY4EB"
# test
#name = "阿鸡"
#URL = "https://www.amazon.co.jp/hz/wishlist/ls/1BXUQQ5TL2GDO?ref_=wl_share"
########################

########## Var #########
global prev_list
global wish_list
# 保存上一次请求得到的愿望单物品数据
prev_list = []
# 保存本次请求得到的愿望单物品数据
wish_list = []
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

async def print_items(bot, items, str):
    if items:
        msg = f"检测到 {name} 的愿望单以下物品被{str}: \r\n"
        for item in items:
            msg += item + "\r\n"
        try:
            #print(msg)
            await bot.send_group_msg(group_id = 235976635, message = msg)
        except:
            pass
 
def check_clear(string):
    # pattern found
    return string.find("このリストにはアイテムはありません") != -1

async def listen():
    global prev_list
    global wish_list
    try:
        bot = nonebot.get_bot()
        text = request(URL, HEADERS)
        wish_list = find_items(text)
        # 如果愿望单突然完全清空，则检查文本中是否确实包含无物品信息
        if not wish_list and not check_clear(text):
            wish_list = prev_list
        new_items = check_items(wish_list, prev_list)
        buyed_items = check_items(prev_list, wish_list)
        prev_list = wish_list
        await print_items(bot, new_items, "添加")
        await print_items(bot, buyed_items, "清除")
    except:
        pass

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(listen, "interval", minutes=10)