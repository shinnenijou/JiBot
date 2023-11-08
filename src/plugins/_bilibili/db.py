# -*- coding: utf-8 -*-
import sqlite3, os
from nonebot.log import logger

# NOTICE: 在本数据库中user指监听推特的对象
# TODO 将数据库调整为异步

DB_PATH = './data/bilibili/bilibili.db'
#  初始化
def init() -> None:  
    """
    主表user_list, 用于保存需要监听的用户信息
    """
    try:
        os.mkdir('./data/bilibili')
    except FileExistsError:
        pass
    _creat_main_table()
    _creat_translator_list()
    _merge_main_table()
    
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
                uid varchar(255) primary key not null,
                room_id varchar(255) not null,
                name varchar(255) not null,
                newest_timestamp int
            );
            """
        )
        connection.commit()
        logger.success('bilibili: 主表初始化成功')
    cursor.close()
    connection.close()

def _creat_translator_list():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    main_table_exist = cursor.execute(
        'select count(*) from sqlite_master where type="table" and name="translator_list";'
        ).fetchone()[0]
    if not main_table_exist:
        cursor.execute(
            """
            create table translator_list (
                qq_id int primary key not null,
                group_id int not null,
                name varchar(255) not null
            );
            """
        )
        connection.commit()
        logger.success('bilibili: 翻译白名单初始化成功')
    cursor.close()
    connection.close()

def _merge_main_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    old_table_exist = cursor.execute(
        'select count(*) from sqlite_master where type="table" and name="user_list_old";'
        ).fetchone()[0]

    print("old_table_exist: ",old_table_exist)
    if old_table_exist == 1:
        cursor.execute('select * from user_list_old;')
        data = cursor.fetchall()
        for row in data:
            cursor.execute(f'insert into user_list values("{row[0]}", "{row[1]}", "{row[2]}", {row[3]});')
        
        cursor.execute('drop table user_list_old;')
        connection.commit()
        
    cursor.close()
    connection.close()
            

# bili用户操作
def add_user(uid:int, room_id, name:str, timestamp:int=0) -> bool:#创建用户对应的表
    """
    新添加一个表用于保存监听该用户的群和相关信息, 由于数字id是唯一标识所以使用下划线+id作为表名
    如果该用户已经存在则什么都不做
    WARNING: 表名十分运维不友好, 手动查表前需要在user_list主表查询user的数字id
    :param uid: bili用于唯一标识用户的数字id, 不可更改
    :param name: 用户显示在个人页面上的名称
    """
    success = True
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    user_exist = cursor.execute(
        f'select count(*) from sqlite_master where type="table" and name="_{uid}";'
        ).fetchone()[0]
    if not user_exist:
        cursor.execute(f'insert into user_list values("{uid}", "{room_id}", "{name}", {timestamp});')
        cursor.execute(
            f"""
            create table _{uid} (
                group_id int primary key not null,
                translate_on int not null
            );
            """
        )
        connection.commit()
    else:
        success = False
        logger.warning(f'表已存在: _{uid}')
    cursor.close()
    connection.close()
    return success

def delete_user(uid:int) -> bool:
    """
    删除一个监听用户, 如果该用户对应的表中已经没有群关注则能删除成功, 否则将返回失败
    WARNING: 表名十分运维不友好, 手动查表前需要在user_list主表查询user的数字id
    :param uid: bili用于唯一标识用户的数字id, 不可更改
    """
    success = False
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    user_exist = cursor.execute(
        f'select count(*) from sqlite_master where type="table" and name="_{uid}";'
        ).fetchone()[0]
    if user_exist:
        group_remain = cursor.execute(f'select count(*) from _{uid}').fetchone()[0]
        if not group_remain:
            cursor.execute(f'drop table _{uid};')
            cursor.execute(f'delete from user_list where uid="{uid}";')
            success = True
            connection.commit()
        else:
            logger.warning(f'{uid}仍有群在订阅中, 删除失败')
    cursor.close()
    connection.close()
    return success

def get_user_groups(uid:int) -> dict[str, int]:
    """
    获取订阅了某位用户的所有群及开启翻译的状况。
    :return group_list: 保存订阅群信息的字典, key为群号, value为是否开启翻译
    """
    group_list = {}
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select * from _{uid};')
    data = cursor.fetchall()
    for row in data:
        group_list[row[0]] = row[1]
    cursor.close()
    connection.close()
    return group_list

def get_user_list() -> dict[str,dict]:
    """
    获取所有bili用户的信息, 用于新推文的请求。
    :return user_list: 保存用户信息的字典, key为uid, value为包含name, newest_timestamp, room的字典
    """
    user_list = {}
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('select * from user_list;')
    data = cursor.fetchall()
    for row in data:
        user_list[row[0]] = {
            'name':row[2],
            'room':row[1],
            'newest_timestamp':row[3]
        }
    cursor.close()
    connection.close()
    return user_list

def get_user_name(uid:int) -> str:
    """
    根据用户名称获取对应的名称
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select name from user_list where uid="{uid}";')
    try:
        data = cursor.fetchone()
        name = data[0]
    except TypeError:
        name = ""
    cursor.close()
    connection.close()
    return name

# 白名单操作
# WARNING: 所有用户共用
def add_translator_list(qq_id:int, group_id:int, name:str) -> bool:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select count(*) from translator_list where qq_id={qq_id} and group_id={group_id};')
    white_list_exist = cursor.fetchone()[0]
    success = False
    if not white_list_exist:
        cursor.execute(f'insert into translator_list values({qq_id},{group_id},"{name}");')
        connection.commit()
        success = True
    cursor.close()
    connection.close()
    return success

def remove_translator_list(qq_id:int, group_id:int) -> str:
    """
    返回: 被移除的用户名称
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select name from translator_list where qq_id={qq_id} and group_id={group_id};')
    result = cursor.fetchall()
    name = ""
    if result:
        name = result[0][0]
        cursor.execute(f'delete from translator_list where qq_id={qq_id} and group_id={group_id};')
        connection.commit()
    cursor.close()
    connection.close()
    return name

def get_translator_list():
    """
    返回当前评论白名单的信息
    :return translator_list: 保存白名单的字典, key为session_id, value为名字
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select qq_id, group_id, name from translator_list;')
    translator_list = {}
    data = cursor.fetchall()
    for row in data:
        translator_list[f'group_{row[1]}_{row[0]}'] = row[2]
    return translator_list

# 群订阅操作
def add_group_sub(uid:int, group_id:int) -> bool: #添加订阅信息
    """
    向已存在的表中插入群记录, 如果群已经存在则什么都不做
    :param uid: 唯一标识用户的数字uid
    :param group_id: 监听该用户的群id
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    success = True
    group_exist = cursor.execute(
        f'select count(*) from _{uid} where group_id={group_id};').fetchone()[0]
    if not group_exist:
        cursor.execute(f'insert into _{uid} values({group_id}, 1);')  # 默认开启翻译
        connection.commit()
    else:
        success = False
        logger.warning(f'群{group_id} 已存在表_{uid}中')
    cursor.close()
    connection.close()
    return success
    
def delete_group_sub(uid:int, group_id:int) -> bool:  #删除订阅信息
    """
    从已存在的表中删除群记录, 如果群不在记录中则什么都不做\n
    :param uid: 唯一标识用户的数字uid
    :param group_id: 监听该用户的群id
    """
    success = True
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    group_exist = cursor.execute(
        f'select count(*) from _{uid} where group_id={group_id};').fetchone()[0]
    if group_exist:
        cursor.execute(f'delete from _{uid} where group_id={group_id};')
        connection.commit()
    else:
        success = False
        logger.warning(f'群{group_id} 不在表_{uid}中')
    cursor.close()
    connection.close()
    return success

def get_group_sub(group_id:int) -> dict[str, dict[str, str]]:
    """
    根据群号搜索该群关注的所有用户
    :return sub_list: 保存订阅信息的字典, key为uid, value为包含name, need_translate的字典
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('select uid, name from user_list')
    user_list = cursor.fetchall()
    sub_list = {}
    for row in user_list:
        id = row[0]
        translate_on = cursor.execute(
            f'select translate_on from _{id} where group_id={group_id};').fetchall()
        if translate_on:
            sub_list[row[0]] = {
                'name':row[1],
                'need_translate':translate_on[0][0]
            }
    return sub_list

# 翻译控制
def translate_on(uid:int, group_id:int) -> bool:  # 开启推文翻译
    sucess = False
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    if not id:
        return sucess
    cursor.execute(f'select count(*) from _{uid} where group_id={group_id};')
    group_exist = cursor.fetchone()[0]
    if group_exist:
        cursor.execute(f'update _{uid} set translate_on=1 where group_id={group_id};')
        sucess = True
        connection.commit()
    cursor.close()
    connection.close()
    return sucess
    
def translate_off(uid:int, group_id:int) -> bool:  # 关闭推文翻译
    sucess = True
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select count(*) from _{uid} where group_id={group_id};')
    group_exist = cursor.fetchone()[0]
    if group_exist:
        cursor.execute(f'update _{uid} set translate_on=0 where group_id={group_id};')
        connection.commit()
    else:
        sucess = False
    cursor.close()
    connection.close()
    return sucess

# 时间戳更新
def update_timestamp(uid:int, newest_timestamp:int):  # 更新某用户最新动态时间戳
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'update user_list set newest_timestamp={newest_timestamp} where uid="{uid}";')
    connection.commit()
    cursor.close()
    connection.close()
