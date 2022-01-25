import requests
import nonebot
from nonebot.plugin import require

########## URL #########
# 乙女音
#url = "https://www.amazon.co.jp/hz/wishlist/ls/1JL7SPMBV2XB2?ref_=wl_fv_le"
# 咪太君
#url = "https://www.amazon.co.jp/gp/aw/ls/ref=aw_wl_lol_wl?ie=UTF8&lid=WQJIE8LKY4EB"
# test
url = "https://www.amazon.jp/hz/wishlist/ls/1BXUQQ5TL2GDO?ref_=wl_share"
########################

########## Var #########
# 保存上一次请求得到的愿望单物品数据
global prev_list
prev_list = []
# 保存本次请求得到的愿望单物品数据
wish_list = []
########################

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

def check_new_list(url):
    # 监听给定url是否包含愿望单物品
    wishlist = []
    try:
        # 向amazon请求网页html
        response = requests.request("GET", url)
        response.encoding = "UTF-8"
        resp = response.text
    except:
        # 发生任何异常都跳出
        resp = ""

    if resp:
        # 如果get没有发生异常，则对返回的html进行处理
        begin = 0
        # 将返回数据中包含的愿望单物品全部添加至列表中
        while begin != -1:
            # 查找愿望单中是否有物品
            item_title, begin = find_item(resp, begin)
            if item_title:
                wishlist.append(item_title)
    return wishlist

def check_items(list1, list2):
    # 比对两个列表，找出list1中不在list2中的元素
    not_include = []
    for item in list1:
        if item not in list2:
            not_include.append(item)
    return not_include

scheduler = require("nonebot_plugin_apscheduler").scheduler
# @scheduler.scheduled_job(
#     "interval",
#     minutes=1
# )

async def listen():
    global prev_list
    wish_list = []
    new_items = []
    buyed_items = []
    bot = nonebot.get_bot()
    wish_list = check_new_list(url)
    if wish_list:
        new_items = check_items(wish_list, prev_list)
        buyed_items = check_items(prev_list, wish_list)
    prev_list = wish_list
    if new_items:
        mymsg = "检测到愿望单新添加如下物品: \r\n"
        for item in new_items:
            mymsg += item + "\r\n"
        try:
            await bot.send_private_msg(user_id = 598374876, message = mymsg)
        except:
            pass
    if buyed_items:
        mymsg = "检测到愿望单以下物品被清: \r\n"
        for item in new_items:
            mymsg += item + "\r\n"
        try:
            await bot.send_private_msg(user_id = 598374876, message = mymsg)
        except:
            pass

scheduler.add_job(listen, "interval", minutes=10)