# -*- coding: utf-8 -*-
import aiohttp
import requests
# HTTP headers line
HEADERS = {}
HEADERS["Host"] = "www.amazon.co.jp"
HEADERS["Accept"] = "text/html"
HEADERS["Accept-Language"] = "ja-JP"
HEADERS["Connection"] = "close"

async def fetch_items(url : str) -> list[str]:
    items = []
#   with aiohttp.ClientSession() as session:
    resp = _request(url, HEADERS)
    new_items = _find_items(resp)
    items.extend(new_items)
        # final_page = True
        # if new_items and new_items % 10:
        #     final_page = False
        # while not final_page:
        #     resp = await _request_next_page(session, url, HEADERS)
        #     new_items = _find_items(resp)
        #     items.extend(new_items)
        #     final_page = True
        #     if new_items and new_items % 10:
        #         final_page = False
    return items, resp

def _request(
    url : str, headers : dict[str, str]) -> str:
    return requests.get(url=url, headers=headers).text
# def _request(
#     session : aiohttp.ClientSession,
#     url : str, headers : dict[str, str] = HEADERS) -> str:
# async def _request_next_page(
#     session : aiohttp.ClientSession,
#     url : str, headers : dict[str, str] = HEADERS) -> str:...

def _find(string : str, begin : int):
    item_beg = string.find("itemName", begin, len(string))
    if item_beg == -1:
        item_title = ""
        end = -1
    else:
        title_beg = string.find("title", item_beg, len(string))
        end = string.find("href", title_beg, len(string))
        item_title = string[title_beg + 7: end - 2].strip()
    return item_title, end

def _find_items(string : str) -> list[str]:
    items = []
    if string:
        # 如果get没有发生异常，则对返回的html进行处理
        begin = 0
        # 将返回数据中包含的愿望单物品全部添加至列表中
        while begin != -1:
            # 查找愿望单中是否有物品
            item_title, begin = _find(string, begin)
            if item_title:
                items.append(item_title)
    return items

def check_items(list1 : list, list2 : list):
    """
    比对两个列表，找出list1中不在list2中的元素
    """
    not_include = []
    for item in list1:
        if item not in list2:
            not_include.append(item)
    return not_include

def make_notice(new_items : list[str],buyed_items : list[str],name : str,url : str): 
    """
    通过给定的new_items和buyed_items构造通知信息, 如果两个items都是空则返回空的字符串
    """ 
    msg = ""
    if new_items:
        msg += f"{name}のほしい物リストに以下の商品が追加されました:\r\n"
        for i in range(len(new_items)):
            msg += f'[{i + 1}]{new_items[i]}\r\n'
        msg += "\r\n"
    if buyed_items:
        msg += f"{name}のほしい物リストに以下の商品が削除されました:\r\n"
        for i in range(len(buyed_items)):
            msg += f'[{i + 1}]{buyed_items[i]}\r\n'
        msg += "\r\n"
    if msg:
        msg += url
    return msg

def check_clear(text : str) -> bool:
    """
    检查请求到的页面是不是真的没有商品。没有商品的页面信息中将会包含相关提示
    """
    return text.find("このリストにはアイテムはありません") != -1