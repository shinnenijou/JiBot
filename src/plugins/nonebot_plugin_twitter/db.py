# -*- coding: utf-8 -*-
import sqlite3, os
from nonebot.log import logger

# NOTICE: 在本数据库中user指监听推特的对象
# TODO 将数据库调整为异步

DB_PATH = './data/twitter/twitter.db'

def init() -> None:  
    """
    主表user_list, 用于保存需要监听的用户信息
    """
    try:
        os.mkdir('./data/twitter')
    except FileExistsError:
        pass

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
    else:
        logger.warning('主表已存在')
    cursor.close()
    connection.close()
    
def add_new_user(id : str, username : str, name : str) -> bool:#创建用户对应的表
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
    
# def show_tables():
#     connection = sqlite3.connect(DB_PATH)
#     cursor = connection.cursor()
#     cursor = cursor.execute('select name from sqlite_master where type="table";')
#     print(*[row[0] for row in cursor.fetchall()])
#     cursor.close()
#     connection.close()

# def show_users():
#     connection = sqlite3.connect(DB_PATH)
#     cursor = connection.cursor()
#     cursor = cursor.execute(f'select * from user_list;')
#     for row in cursor.fetchall():
#         print(row)
#     cursor.close()
#     connection.close()

# def show_table(id:str):
#     connection = sqlite3.connect(DB_PATH)
#     cursor = connection.cursor()
#     cursor = cursor.execute(f'select * from _{id};')
#     for row in cursor.fetchall():
#         print(row)
#     cursor.close()
#     connection.close()

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
    从已存在的表中删除群记录, 如果群不在记录中则什么都不做
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

def get_all_users() -> tuple[list[str], list[str], list[str]]:
    """
    获取所有推特用户的信息, 用于新推文的请求。所有返回值的索引一一对应
    :return id_list: 保存用户数字id的列表
    :return name_list: 保存每个用户显示名称的列表
    :return newest_tweet_list: 保存每个用户最新推文id的列表
    """
    id_list = []
    username_list = []
    name_list = []
    newest_tweet_list = []
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('select * from user_list;')
    data = cursor.fetchall()
    for row in data:
        id_list.append(row[0])
        username_list.append(row[1])
        name_list.append(row[2])
        newest_tweet_list.append(row[3])
    cursor.close()
    connection.close()
    return id_list, username_list, name_list, newest_tweet_list
        
def get_all_groups(id : str) -> tuple[list[str], list[int]]:
    """
    获取订阅了某位用户的所有群。所有返回的列表索引一一对应
    :return group_list: 保存群号的列表
    :return translate_on_list: 保存群是否开启翻译的列表
    """
    group_list = []
    translate_on_list = []
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'select * from _{id};')
    data = cursor.fetchall()
    for row in data:
        group_list.append(row[0])
        translate_on_list.append(row[1])
    cursor.close()
    connection.close()
    return group_list, translate_on_list
    
def get_id_n_name(username : str) -> str:
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

def get_group_users(group_id : str) -> tuple[list[str],list[str],list[str]]:
    """
    根据群号搜索该群关注的所有用户, 返回的列表索引一一对应
    :return id_list: 用户数字id列表
    :return username_list: 用户id列表
    :return name_list: 用户名称列表
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('select id,username,name from user_list')
    user_list = cursor.fetchall()
    id_list = []
    username_list = []
    name_list = []
    for row in user_list:
        id = user_list[0]
        group_exist = cursor.execute(
            f'select count(*) from _{id} where group_id="{group_id}";').fetchone()[0]
        if group_exist:
            id_list.append(row[0])
            username_list.append(row[1])
            name_list.append(row[2])
    return id_list, name_list, username_list

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

def update_newest_tweet(id : str, newest_tweet_id : str):  # 更新某用户最新推文ID
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f'update user_list set newest_tweet_id="{newest_tweet_id}" where id="{id}"')
    connection.commit()
    cursor.close()
    connection.close()