# -*- coding: utf-8 -*-
# python STL
import sqlite3
from os import mkdir

STAFF_DIR_PATH = f'./data/staff'
DB_PATH = f'{STAFF_DIR_PATH}/staff.db'

# 初始化
def init() -> None:
    """
    初始化数据库, 初始化包含一个主表subtitle_group, 用于保存使用该人员管理功能的组群(需要手动添加)
    """
    try:
        mkdir(STAFF_DIR_PATH)
    except FileExistsError:
        pass
    _creat_group_list()

def _creat_group_list():
    """
    创建subtitle_group主表
    """
    with sqlite3.connect(DB_PATH) as  connection:
        cursor = connection.cursor()
        # 检查主表是否已存在
        table_exist = cursor.execute(
            'select count(*) from sqlite_master where type="table" and name="subtitle_group";'
        ).fetchone()[0]
        # 不存在则新建
        if not table_exist:
            cursor.execute(
                """
                create table subtitle_group (
                    group_id int primary key not null,
                    group_name varchar(255) not null);
                """
            )
            connection.commit()
        cursor.close()

# 主表管理
# subtitle_group: group_id, group_name
def get_group_list() -> dict[int, str]:
    """
    查询所有已注册的字幕组群
    :return group_list: key为群号, value为组名的字典
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        data = cursor.execute('select * from subtitle_group;').fetchall()
        group_list = {}
        for row in data:
            group_list[row[0]] = row[1]
        cursor.close()
    return group_list

def is_registered(group_id: int) -> bool:
    """
    查询某群是否已经注册为字幕组
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        group_exist = cursor.execute(
            f'select count(*) from subtitle_group where group_id={group_id};').fetchone()[0]
        cursor.close()
    return bool(group_exist)

def add_group(group_id: int, group_name: str) -> bool:
    """
    注册一个字幕组群, 同时创建该组的人员表。该组已存在则返回False。
    :param proup_id: 群号
    :param group_name: 组名, 可以不于群名相同
    """
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        # 检查该组是否已注册
        group_exist = cursor.execute(
            f'select count(*) from subtitle_group where group_id={group_id};').fetchone()[0]
        # 未注册则向主表添加信息，并创建该组人员表
        if not group_exist:
            cursor.execute(f'insert into subtitle_group values({group_id}, "{group_name}");')
            cursor.execute(
                f"""
                create table _{group_id} (
                    qq_id int primary key not null,
                    name varchar(255) not null,
                    occupation int not null
                );
                """
            )
            connection.commit()
            success = True
        cursor.close()
    return success

def delete_group(group_id: int) -> bool:
    """
    删除一个已注册的字幕组。WARNING: 会同时删除该组的人员表, 调用该函数时必须进行确认, 并且严格管理权限
    :param proup_id: 群号
    """
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        # 检查该组是否已经注册
        group_exist = cursor.execute(
            f'select count(*) from subtitle_group where group_id={group_id};').fetchone()[0]
        # 已注册则删除主表条目, 并且删除对应人员表
        if group_exist:
            cursor.execute(f'delete from subtitle_group where group_id={group_id};')
            cursor.execute(f'drop table _{group_id};')
            connection.commit()
            success = True
        cursor.close()
    return success

# 人员表管理
# _group_id: qq_id, name, occupation
def get_all_staff(group_id: int) -> dict[int, dict]:
    """
    查询一个组群内所有已注册的人员
    :return staff_list: key为qq号, value为包含name, occupation的字典的字典
    :param group_id: 群号
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        data = cursor.execute(f'select qq_id, name, occupation from _{group_id};').fetchall()
        staff_list = {}
        for row in data:
            staff_list[row[0]] = {'name': row[1], 'occupation':row[2]}
        cursor.close()
    return staff_list

def get_occupation_staff(group_id: int, mask: int) -> dict[int, dict]:
    """
    查询一个组群内某个特定职位的人员
    :return staff_list: key为qq号, value为包含name, occupation的字典的字典
    :param 
    :param mask: 掩码, 通过与运算提取人员occupation中特定职位信息
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        data = cursor.execute(f'select qq_id, name, occupation from _{group_id};').fetchall()
        staff_list = {}
        for row in data:
            if row[2] & mask:
                staff_list[row[0]] = {'name':row[1], 'occupation': row[2]}
        cursor.close()
    return staff_list

def get_one_staff(group_id: int, qq_id: int) -> dict[int, dict]:
    """
    获取某个人员的职位
    """
    with sqlite3.connect(DB_PATH) as connection:
        staff_info = {}
        cursor = connection.cursor()
        staff_exist = cursor.execute(
            f"select count(*) from _{group_id} where qq_id={qq_id};").fetchone()[0]
        if staff_exist:
            row = cursor.execute(
            f"select * from _{group_id} where qq_id={qq_id};").fetchone()
            staff_info = {row[0]: {'name':row[1], 'occupation': row[2]}}
        cursor.close()
    return staff_info

def add_occupation(group_id: int, qq_id: int, name:str,  occupation: int) -> bool:
    """
    新增人员的职位, 掩码使用或运算
    :return: 是否"更新"成功, 新增条目返回False, 更新则返回True
    """
    # 先尝试直接创建新条目, 如果失败则对条目内的职位进行update
    if _add_staff(group_id, qq_id, name, occupation):
        return False
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        data = cursor.execute(
            f"select occupation from _{group_id} where qq_id={qq_id};").fetchone()[0]
        data = data | occupation
        cursor.execute(f'update _{group_id} set occupation={data} where qq_id={qq_id};')
        connection.commit()
        cursor.close()
    return True

def remove_occupation(group_id: int, qq_id: int, occupation: int) -> bool:
    """
    减少人员的职位, 掩码使用与非运算.注意该函数不会处理无职位的条目
    """
    success = False
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        # 查询是否有此人记录
        staff_exist = cursor.execute(
            f"select count(*) from _{group_id} where qq_id={qq_id};").fetchone()[0]
        if staff_exist:
            data = cursor.execute(
                f"select occupation from _{group_id} where qq_id={qq_id};").fetchone()[0]
            # 或非运算将掩码1位置上的数变成0
            data = data & ~occupation
            cursor.execute(f'update _{group_id} set occupation={data} where qq_id={qq_id};')
            connection.commit()
            cursor.close()   
            success = True
    return success

def _add_staff(group_id: int, qq_id: int, name: str, occupation:int) -> bool:
    """
    注册一个字幕组成员, 注册成功返回True, 已存在返回False.
    :param group_id: 群号
    :param qq_id: 注册人qq号
    :param name: 注册人自定义名字
    :param occupation: 注册人职位. 取职位映射数字的和. 1 剪辑, 2 时轴, 4翻译, 8 校对, 16 美工, 32 特效轴, 64 后期, 128 皮套, 256 画师, 512 同传
    """
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        # 查询该人员是否已注册
        staff_exist = cursor.execute(
            f'select count(*) from _{group_id} where qq_id={qq_id};').fetchone()[0]
        # 该群已注册但人员不存在则创建新条目
        if not staff_exist:
            cursor.execute(f'insert into _{group_id} values({qq_id}, "{name}", {occupation});')
            connection.commit()
            success = True
        cursor.close()
    return success

def _remove_staff(group_id: int, qq_id: int) -> bool:
    """
    移除一个已注册的字幕组成员。
    :param group_id: 群号
    :param qq_id: 注册人qq号
    """
    with sqlite3.connect(DB_PATH) as connection:
        success = False
        cursor = connection.cursor()
        # 查询是否有该人员记录
        staff_exist = cursor.execute(
            f'select count(*) from _{group_id} where qq_id={qq_id};').fetchone()[0]
        # 存在则移除创建新条目
        if staff_exist:
            cursor.execute(f'delete from _{group_id} where qq_id={qq_id};')
            connection.commit()
            success = True
        cursor.close()
    return success

