# -*- coding: utf-8 -*-
from cgitb import text
from inspect import Parameter
import aiohttp
import requests
import asyncio
import nonebot
from nonebot.log import logger
from tortoise import BackwardFKRelation
# HTTP headers line
HEADERS = {}
HEADERS["Host"] = "www.amazon.co.jp"
HEADERS["Accept"] = "text/html"
HEADERS["Accept-Language"] = "ja-JP"
HEADERS["Connection"] = "close"
# CONSTANT
PROXY = nonebot.get_driver().config.dict()['proxy']
PROXY = None if PROXY == 'None' else PROXY
BARK_URL = nonebot.get_driver().config.dict()['bark_url']

async def _push_to_bark(msg):
    """
    将消息推送至Bark
    """
    result = {}
    async with aiohttp.ClientSession() as session:
        url = BARK_URL + "/" + msg
        async with session.get(url=url) as resp:
            result = await resp.json()
    return result["code"] == 200

async def push_to_bark(msg):
    """
    包装函数, 对发送失败的内容进行重试
    """
    retry_time = 5
    for i in range(retry_time):
        if await _push_to_bark(msg):
            break

async def request_many(*urls:int) -> list[str]:
    """
    获取复数url的愿望单页面
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            tasks.append(asyncio.create_task(_request(session, url, HEADERS)))
        wishlist_list = await asyncio.gather(*tasks)
    return wishlist_list

async def _request(session:aiohttp.ClientSession, url:str, headers:dict[str,str]) -> str:
    """
    获取单一url的愿望单页面
    """
    async with session.get(url=url, headers=headers, proxy=PROXY) as resp:
        try:
            text = await resp.text()
        except Exception as err:
            text = ""
            logger.error(f'请求愿望单时发生错误: {err}')
    return text

def _find_one(string:str, begin:int):
    item_beg = string.find("itemName", begin, len(string))
    if item_beg == -1:
        item_title = ""
        end = -1
    else:
        title_beg = string.find("title", item_beg, len(string))
        end = string.find("href", title_beg, len(string))
        item_title = string[title_beg + 7: end - 2].strip()
    return item_title, end

def find_all(string:str) -> list[str]:
    items = []
    if string:
        # 如果get没有发生异常，则对返回的html进行处理
        begin = 0
        # 将返回数据中包含的愿望单物品全部添加至列表中
        while begin != -1:
            # 查找愿望单中是否有物品
            item_title, begin = _find_one(string, begin)
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

def make_notice(new_items: list[str], buyed_items: list[str], url: str): 
    """
    通过给定的new_items和buyed_items构造通知信息, 如果两个items都是空则返回空的字符串
    """ 
    msg = ""
    if new_items:
        msg += "--------------------\n"
        msg += f"以下の商品が追加されました:\n"
        for i in range(len(new_items)):
            msg += f'[{i + 1}]{new_items[i]}\n'
    if buyed_items:
        msg += "--------------------\n"
        msg += f"以下の商品が削除されました:\n"
        for i in range(len(buyed_items)):
            msg += f'[{i + 1}]{buyed_items[i]}\n'
    if msg:
        msg += "--------------------\n"
        msg += url
    return msg

def is_clear(text : str) -> bool:
    """
    检查请求到的页面是不是真的没有商品。没有商品的页面信息中将会包含相关提示
    """
    return text.find("このリストにはアイテムはありません") >= 0

def lid_to_url(*lid_list: str) -> list[str]:
    """
    将用户lid转换为对应的url进行请求
    """
    return [f'https://www.amazon.co.jp/hz/wishlist/ls/{lid}' for lid in lid_list]