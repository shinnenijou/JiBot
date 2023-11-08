# -*- coding: utf-8 -*-
import sqlite3, os
from nonebot.log import logger

# NOTICE: 在本数据库中user指监听推特的对象
# TODO 将数据库调整为异步

DB_PATH = './data/twitter/twitter.db'
#  初始化
def init() -> None:  
    """
    主表user_list, 用于保存需要监听的用户信息
    """
    try:
        os.mkdir('./data/twitter')
    except FileExistsError:
        pass
    _creat_main_table()
    _creat_white_list()
    
def _creat_main_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    main_table_exist = cursor.execute(
        'select count(*) from sqlite_master where type="table" and name="user_list";'
        ).fetchone()[0]
    if not main_table_exist:
        cursor.execute(
            """
            create table user_list (
                id varchar(255) primary key not null,
                username varchar(255) not null,
                name varchar(255) not null,
                newest_tweet_id varchar(255)
            );
            """
        )
        connection.commit()
        logger.success('Twitter: 主表初始化成功')
    cursor.close()
    connection.close()

def _creat_white_list():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    main_table_exist = cursor.execute(
        'select count(*) from sqlite_master where type="table" and name="white_list";'
        ).fetchone()[0]
    if not main_table_exist:
        cursor.execute(
            """
            create table white_list (
                id varchar(255) primary key not null,
                username varchar(255) not null,
                name varchar(255) not null
            );
            """
        )
        connection.commit()
        logger.success('Twitter: 白名单初始化成功')
    cursor.close()
    connection.close()

# 推特用户操作
def add_user(id : str, username : str, name : str) -> bool:#创建用户对应的表
    """
    新添加一个表用于保存监听该用户的群和相关信息, 由于数字id是唯一标识所以使用下划线+id作为表名
    如果该用户已经存在则什么都不做
    WARNING: 表名十分运维不友好, 手动查表前需要在user_list主表查询user的数字id
    :param id: 推特后台用于唯一标识用户的数字id, 不可更改
    :param username: @后的id, 可以被用户自定义更改
    :param name: 用户显示在个人页面上的名称
    """
    success = True
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    table_exist = cursor.execute(
        f'select count(*) from sqlite_master where type="table" and name="_{id}";'
        ).fetchone()[0]
    if not table_exist:
        # 初始的newest_tweet_id为空
        cursor.execute(f'insert into user_list values("{id}", "{username}", "{name}", "");')
        cursor.execute(
            f"""
            create table _{id} (
                group_id char(20) primary key not null,
                translate_on int not null
            );
            """
        )
        connection.commit()
    else:
        success = False
        logger.warning(f'表已存在: _{id}')
    cursor.close()
    connection.close()
    return success

def get_user_groups(id : str) -> dict[str,int]:
    """
    获取订阅了某位用户的所有群及开启翻译的状况
    :return group_list: 保存群号的字典, key为群号, value为是否需要翻译
    """
    group_list = {}
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select * from _{id};')
    data = cursor.fetchall()
    for row in data:
        group_list[row[0]] = row[1]
    cursor.close()
    connection.close()
    return group_list

def get_user_list() -> dict[str,dict]:
    """
    获取所有推特用户的信息, 用于新推文的请求
    :return user_list: key为id, 包含name, username, newest_id的字典
    """
    user_list = {}
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('select * from user_list;')
    data = cursor.fetchall()
    for row in data:
        user_list[row[0]] = {'name':row[2], 'username':row[1], 'newest_id':row[3]}
    cursor.close()
    connection.close()
    return user_list

def get_user_id_name(username : str) -> str:
    """
    根据用户id(非数字id)获取对应的数字id和名称
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select id, name from user_list where username="{username}";')
    try:
        data = cursor.fetchone()
        id = data[0]
        name = data[1]
    except TypeError:
        id = ""
        name = ""
    cursor.close()
    connection.close()
    return id, name

# 白名单操作
# WARNING: 所有推特用户共用
def add_white_list(id:str, username:str, name:str) -> bool:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select count(*) from white_list where id="{id}";')
    white_list_exist = cursor.fetchone()[0]
    success = False
    if not white_list_exist:
        cursor.execute(f'insert into white_list values("{id}","{username}","{name}");')
        connection.commit()
        success = True
    cursor.close()
    connection.close()
    return success

def remove_white_list(username:str) -> str:
    """
    返回被移除的用户名称
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select name from white_list where username="{username}";')
    result = cursor.fetchall()
    name = ""
    if result:
        name = result[0][0]
        cursor.execute(f'delete from white_list where username="{username}";')
        connection.commit()
    cursor.close()
    connection.close()
    return name

def get_white_list() -> dict[str,dict]:
    """
    获取白名单列表
    :return white_list: key为id, value为包含name, username的字典的字典
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select id, username, name from white_list;')
    white_list = {}
    data = cursor.fetchall()
    for row in data:
        white_list[row[0]] = {'username':row[1], 'name':row[2]}
    return white_list

# 群订阅操作
def add_group_sub(id : str, group_id : str) -> bool: #添加订阅信息
    """
    向已存在的表中插入群记录, 如果群已经存在则什么都不做
    :param id: 唯一标识用户的数字id
    :param group_id: 监听该用户的群id
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    success = True
    group_exist = cursor.execute(
        f'select count(*) from _{id} where group_id="{group_id}";').fetchone()[0]
    if not group_exist:
        cursor.execute(f'insert into _{id} values("{group_id}", 1);')  # 默认开启翻译
        connection.commit()
    else:
        success = False
        logger.warning(f'群{group_id} 已存在表_{id}中')
    cursor.close()
    connection.close()
    return success
    
def delete_group_sub(id : str, group_id : str) -> bool:  #删除订阅信息
    """
    从已存在的表中删除群记录, 如果群不在记录中则什么都不做\n
    NOTICE: 删除某个用户的最后一条群记录时将会同时删除user_list中的记录
    :param id: 唯一标识用户的数字id
    :param group_id: 监听该用户的群id
    """
    success = True
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    group_exist = cursor.execute(
        f'select count(*) from _{id} where group_id="{group_id}";').fetchone()[0]
    if group_exist:
        cursor.execute(f'delete from _{id} where group_id="{group_id}";')
        group_remain = cursor.execute(f'select count(*) from _{id}').fetchone()[0]
        if not group_remain:
            cursor.execute(f'drop table _{id};')
            cursor.execute(f'delete from user_list where id="{id}";')
        connection.commit()
    else:
        success = False
        logger.warning(f'群{group_id} 不在表_{id}中')
    cursor.close()
    connection.close()
    return success

def get_group_sub(group_id : str) -> dict[str, dict]:
    """
    根据群号搜索该群关注的所有用户
    :return sub_list: key为id, value为包含username, name, need_translate的字典的字典
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('select id,username,name from user_list')
    user_list = cursor.fetchall()
    sub_list = {}
    for row in user_list:
        id = row[0]
        translate_on = cursor.execute(
            f'select translate_on from _{id} where group_id="{group_id}";').fetchall()
        if translate_on:
            sub_list[row[0]] = {'name':row[2], 'username':row[1],
                'need_translate': translate_on[0][0]}
    return sub_list

# 翻译控制
def translate_on(id : str, group_id : str) -> bool:  # 开启推文翻译
    sucess = False
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    if not id:
        return sucess
    cursor.execute(f'select count(*) from _{id} where group_id="{group_id}";')
    group_exist = cursor.fetchone()[0]
    if group_exist:
        cursor.execute(f'update _{id} set translate_on=1 where group_id="{group_id}";')
        sucess = True
        connection.commit()
    cursor.close()
    connection.close()
    return sucess
    
def translate_off(id : str, group_id : str) -> bool:  # 关闭推文翻译
    sucess = True
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select count(*) from _{id} where group_id="{group_id}";')
    group_exist = cursor.fetchone()[0]
    if group_exist:
        cursor.execute(f'update _{id} set translate_on=0 where group_id="{group_id}";')
        connection.commit()
    else:
        sucess = False
    cursor.close()
    connection.close()
    return sucess

# 时间线更新
def update_newest_tweet(id : str, newest_tweet_id : str):  # 更新某用户最新推文ID
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'update user_list set newest_tweet_id="{newest_tweet_id}" where id="{id}"')
    connection.commit()
    cursor.close()
    connection.close()
