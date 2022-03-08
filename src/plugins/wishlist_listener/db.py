# -*- coding: utf-8 -*-
import sqlite3
from sqlite3 import OperationalError
from os import mkdir

DATA_PATH = './data'
WL_PATH = f'{DATA_PATH}/wishlist_listener'
DB_PATH = f'{WL_PATH}/wishlists.db'

def init() -> None:
    try:
        mkdir(DATA_PATH)
    except FileExistsError:
        pass
    try:
        mkdir(WL_PATH)
    except FileExistsError:
        pass
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    # 监听信息表(主表)
    try:
        cursor = cursor.execute(
            """
            CREATE TABLE WISHLISTS (
                ID INT PRIMARY KEY NOT NULL,
                GROUP_ID INT NOT NULL,
                TARGET_NAME VARCHAR(255) NOT NULL,
                URL VARCHAR(255) NOT NULL
            );
            """
        )
    except OperationalError:
        pass
    count = cursor.execute('SELECT count(*) FROM WISHLISTS;').fetchone()[0]
    if count == 0:
        cursor.execute(
            f"""
            INSERT INTO WISHLISTS VALUES(0, -1, 'NULL', 'NULL');
            """.strip()
        )
    connection.commit()
    connection.close()

async def show_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.execute("select name from sqlite_master where type='table'")
    return cursor.fetchall()

async def select(
    table_name: str,
    group_id : int = None,
    target_name : str = None,
    url : str = None,
    commodity: str = None) -> list:

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    condition = "WHERE ID != 0 AND "
    if group_id:
        condition += f"GROUP_ID = {group_id} AND "
    if target_name:
        condition += f"TARGET_NAME = '{target_name.strip()}' AND "
    if url:
        condition += f"URL = '{url.strip()}' AND "
    if commodity:
        condition += f"COMMODITY = '{commodity.strip()}' AND "
    cursor = cursor.execute(
        f"""
        SELECT * FROM {table_name.strip()} {condition.strip()[:-4]};
        """
    )
    ret = cursor.fetchall()
    connection.close()
    return ret

async def creat_table(target_name:str) -> bool:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            CREATE TABLE {target_name.strip()} (
                ID INT PRIMARY KEY NOT NULL,
                COMMODITY VARCHAR(255) NOT NULL
            )
            """
        )
        status = True
    except OperationalError:
        status = False
    count = cursor.execute(f'SELECT count(*) FROM {target_name.strip()};').fetchone()[0]
    if count == 0:
        cursor.execute(
            f"""
            INSERT INTO {target_name.strip()} VALUES(0, 'None');
            """.strip()
        )
    connection.commit()
    connection.close()
    return status
    
async def insert_list(
    group_id :int = None,
    target_name : str = None,
    url : str = None) -> bool:

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    status = False
    if not await select('wishlists', target_name=target_name):
        await creat_table(target_name)
    if not await select('wishlists', group_id, target_name):
        id = cursor.execute('SELECT MAX(ID) FROM WISHLISTS;').fetchone()[0] + 1
        cursor = connection.cursor()
        cursor.execute(
            f"""
            INSERT INTO WISHLISTS VALUES(
            {id}, {group_id}, '{target_name.strip()}', '{url.strip()}');
            """.strip()
        )
        connection.commit()
        status = True
    connection.close()
    return status

async def delete_list(
    group_id : int = None,
    target_name : str = None) -> bool:

    if not group_id and not target_name:
        return False
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    status = False
    if await select('wishlists', group_id, target_name):
        condition = ''
        if group_id:
            condition += f"GROUP_ID = {group_id} AND "
        if target_name:
            condition += f"TARGET_NAME = '{target_name.strip()}' AND "
        cursor = cursor.execute(
            f"""
            DELETE FROM WISHLISTS WHERE {condition.strip()[:-4]};
            """
        )
        count = cursor.execute(f"SELECT count(*) FROM " + \
            f"WISHLISTS WHERE TARGET_NAME = '{target_name.strip()}';").fetchone()[0]
        if not count:
            cursor.execute(
                f"""
                DROP TABLE {target_name.strip()}
                """
            )
        connection.commit()
        status = True        
    connection.close()
    return status

async def insert_commodity(
    target_name : str,
    commodity : str) -> bool:

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    status = False
    if await select('wishlists', target_name=target_name):
        if not await select(f'{target_name}', commodity=commodity):
            id = cursor.execute(
                f'SELECT MAX(ID) FROM {target_name.strip()};').fetchone()[0] + 1
            cursor = connection.cursor()
            cursor.execute(
            f"""
            INSERT INTO {target_name.strip()} VALUES({id}, '{commodity.strip()}');
            """.strip()
            )
            connection.commit()
            status = True        
    connection.close()
    return status

async def delete_commodity(
    target_name : str,
    commodity : str) -> bool:

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    status = False
    if await select('wishlists', target_name=target_name):
        if await select(f'{target_name}', commodity=commodity):
            cursor = connection.cursor()
            cursor.execute(
            f"""
            DELETE FROM {target_name.strip()} WHERE COMMODITY='{commodity.strip()}';
            """.strip()
            )
            connection.commit()
            status = True        
    connection.close()
    return status