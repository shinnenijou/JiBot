# -*- coding: utf-8 -*-
from locale import currency
import sqlite3
from sqlite3 import OperationalError
from os import mkdir
from sre_constants import SUCCESS
from typing import Tuple
import time

from loguru import logger

DATA_PATH = './data'
WISHLIST_DIR_PATH = f'{DATA_PATH}/wishlist'
DB_PATH = f'{WISHLIST_DIR_PATH}/wishlist.db'

# message log
def message_log(str:str):
    with open(f"{WISHLIST_DIR_PATH}/msg.log", "a") as file:
        file.write(time.asctime() + str + "\n")

# 数据库初始化
def init() -> None:
    """
    初始化数据库,如果没有user_list则创建新表
    """
    try:
        mkdir(DATA_PATH)
    except FileExistsError:
        pass
    try:
        mkdir(WISHLIST_DIR_PATH)
    except FileExistsError:
        pass      
    _creat_user_list()

def _creat_user_list():
    """
    创建用于保存监听对象信息的主表。Amazon愿望单url中的lid为愿望单唯一标识, 主表仅含lid一项
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    # 检查主表是否存在
    table_exist = cursor.execute(
        'select count(*) from sqlite_master where type="table" and name="user_list";'
    ).fetchone()[0]
    # 不存在则创建新表
    if not table_exist:
        cursor = cursor.execute('create table user_list(lid varchar(255) primary key not null);')
        connection.commit()
    cursor.close()
    connection.close()
    
# 监听用户管理
# 主表columns: lid
def get_user_list() -> list[str]:
    """
    获取监听对象lid的列表
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        data = cursor.execute(
            f"""
            select lid from user_list;
            """
        ).fetchall()
        user_list = [row[0] for row in data]
        cursor.close()
    return user_list

def add_user(lid: str) -> bool:
    """
    向user_list添加监听对象(注意: 该函数不用于群订阅操作)
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    """
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        # 查看主表中是否已有记录
        user_exist = cursor.execute(
            f'select count(*) from user_list where lid="{lid}";').fetchone()[0]
        # 如果没有记录则插入新条目
        if not user_exist:
            cursor.execute(f'insert into user_list values("{lid}");')
            # 同时创建用于保存订阅信息的表和现有商品的表
            cursor.execute(
                f'create table sub_{lid} (group_id int primary key not null, name varchar(255) not null);')
            cursor.execute(
                f'create table item_{lid} (item_name varchar(255) not null, add_time int, delete_time int, status int not null);')
            connection.commit()
            success = True
        cursor.close()
    return success

def delete_user(lid: str) -> bool:
    """
    从user_list移除监听对象(注意: 该函数不用于群订阅操作)
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    """
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        # 查看主表中是否已有记录
        user_exist = cursor.execute(
            f'select count(*) from user_list where lid="{lid}";').fetchone()[0]
        # 如果有记录则进行删除
        if user_exist:
            cursor.execute(f'delete from user_list where lid="{lid}";')
            # 同时删除用于保存订阅信息的表和现有商品的表
            cursor.execute(f'drop table sub_{lid};')
            cursor.execute(f'drop table item_{lid};')
            connection.commit()
            success = True
        cursor.close()
    return success

# 群订阅管理
# 订阅表columns: group_id, name
def get_group_sub(group_id: int) -> dict[str,str]:
    """
    获取某个群订阅的所有用户
    :return sub_list: 一个包含所有订阅的字典, key为lid, value为该群提交的订阅用户name
    :param group_id: 群号
    """
    with sqlite3.connect(DB_PATH) as connection:
        sub_list = {}
        cursor = connection.cursor()
        data = cursor.execute(f'select lid from user_list;').fetchall()
        for row in data:
            lid = row[0]
            name = cursor.execute(
                f'select name from sub_{lid} where group_id={group_id};').fetchone()[0]
            sub_list[lid] = name
        cursor.close()
    return sub_list

def get_sub_group(lid: str) -> dict[int, str]:
    """
    获取订阅了某个用户的所有群信息
    :return group_list: 一个包含所有群的字典, key为群号, value为该群提交的订阅用户name
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    """
    with sqlite3.connect(DB_PATH) as connection:
        group_list = {}
        cursor = connection.cursor()
        data = cursor.execute(f'select group_id, name from sub_{lid};').fetchall()
        for row in data:
            group_id = row[0]
            name = row[1]
            group_list[group_id] = name
        cursor.close()        
    return group_list

def add_sub(lid: str, group_id: int, name: str) -> bool:
    """
    为某个群添加订阅, 如果该用户是第一次被订阅, 则会同时添加主表条目, 创建订阅表与商品表
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    :param group_id: 群号
    :param name: 该群提交的订阅用户name, 用于推送时显示
    """
    add_user(lid)  # 添加该用户至主表(变相检查用户及相关表是否存在)
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        already_sub = cursor.execute(f'select count(*) from sub_{lid} where group_id={group_id};').fetchone()[0]
        if not already_sub:
            cursor.execute(f'insert into sub_{lid} values({group_id}, "{name}");')
            connection.commit()
            success = True
        cursor.close()        
    return success

def delete_sub(lid: str, group_id: int) -> bool:
    """
    为某个群移除订阅, 如果该用户不再有群订阅, 则删除主表条目和订阅表, 商品表
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    :param group_id: 群号
    :param name: 该群提交的订阅用户name, 用于推送时显示
    """
    add_user(lid)  # 添加该用户至主表(变相检查用户及相关表是否存在)
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        already_sub = cursor.execute(f'select group_id, name from sub_{lid};').fetchone()[0]
        if already_sub:
            cursor.execute(f'delete from sub_{lid} where group_id={group_id};')
            connection.commit()
            success = True
        # 在删除一条订阅后检查此时订阅表是否为空
        sub_empty = cursor.execute(f'select count(*) from sub_{lid};').fetchone()[0] == 0    
        cursor.close()
    # 订阅表为空则删除该用户订阅表, 商品表, 以及主表记录
    if sub_empty:
        delete_user(lid)
    return success

def delete_group(group_id: int) -> None:
    """
    移除某个群的所有订阅
    :param group_id: 群号
    """
    sub_list = get_group_sub(group_id)
    for lid in sub_list.keys():
        delete_sub(lid, group_id)

# 商品管理
# 商品表clolumn: item_name
def get_items(lid: str) -> list[str]:
    """
    获取某个用户愿望单中现存的所有物品
    :return item_list: 商品名列表
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(f'select item_name from item_{lid} where status=0;')
        item_list = [row[0] for row in cursor.fetchall()]
        cursor.close()
    return item_list

def update_items(lid: str, new_items: list[str], removed_items: list[str]) -> None:
    """
    更新商品表中的, 新增商品和移除商品的数据
    :param lid: 愿望单url中的lid, 可以为唯一标识一个Amazon账号开设的愿望单
    :param new_items: 新增商品名列表
    :param removed_items: 被移除商品名列表
    """
    with sqlite3.connect(DB_PATH) as connection:
        timestamp = int(time.time())
        cursor = connection.cursor()
        for item in removed_items:
            cursor.execute(f'update item_{lid} set delete_time={timestamp} where where item_name="{item}" and status=0;')
            cursor.execute(f'update item_{lid} set status=1 where item_name="{item}" and status=0;')
        for item in new_items:
            cursor = cursor.execute(f'insert into item_{lid} values("{item}", {timestamp}, 0, 0);')
        connection.commit()    
        cursor.close()