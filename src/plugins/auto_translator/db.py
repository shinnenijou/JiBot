# -*- coding: utf-8 -*-
import sqlite3
from sqlite3 import OperationalError
from os import mkdir

DATA_PATH = './data'
UT_DIR_PATH = f'{DATA_PATH}/auto_translator'
DB_PATH = f'{UT_DIR_PATH}/users.db'


def init() -> None:
    try:
        mkdir(DATA_PATH)
    except FileExistsError:
        pass
    try:
        mkdir(UT_DIR_PATH)
    except FileExistsError:
        pass
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    try:
        cursor = cursor.execute(
            """
            CREATE TABLE TRANSLATE(
                ID INT PRIMARY KEY NOT NULL,
                GROUP_ID INT NOT NULL,
                USER_ID INT NOT NULL,
                SOURCE CHAR(5) NOT NULL,
                TARGET CHAR(5) NOT NULL
            );
            """
        )
    except OperationalError:
        pass
    count = cursor.execute('SELECT count(*) FROM TRANSLATE;').fetchone()[0]
    if count == 0:
        cursor.execute(
            f"""
            INSERT INTO TRANSLATE VALUES(0, -1, -1, 'NULL', 'NULL');
            """.strip()
        )
    connection.commit()
    connection.close()

async def insert(group_id :int, user_id : int, source : str, target : str) -> bool:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    if not await select(group_id, user_id, source, target):
        id = cursor.execute('SELECT MAX(ID) FROM TRANSLATE;').fetchone()[0] + 1
        cursor = connection.cursor()
        cursor.execute(
            f"""
            INSERT INTO TRANSLATE VALUES(
            {id}, {group_id}, {user_id}, '{source}', '{target}');
            """.strip()
        )
        connection.commit()
        status = True
    else:
        status = False
    connection.close()
    return status

async def delete(
    group_id : int = None,
    user_id : int = None,
    source : str = None,
    target : str = None) -> bool:

    if not group_id and not user_id and not source and not target:
        return False
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    if await select(group_id, user_id, source, target):
        condition = ''
        if group_id:
            condition += f"GROUP_ID = {group_id} AND "
        if user_id:
            condition += f"USER_ID = {user_id} AND "
        if source:
            condition += f"SOURCE = '{source.strip()}' AND "
        if target:
            condition += f"TARGET = '{target.strip()}' AND "
        cursor.execute(
            f"""
            DELETE FROM TRANSLATE WHERE {condition.strip()[:-4]};
            """
        )
        connection.commit()
        status = True
    else:
        status = False
    connection.close()
    return status

async def select(
    group_id : int = None,
    user_id : int = None,
    source : str = None,
    target : str = None) -> list:

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    condition = "WHERE ID != 0 AND "
    if group_id:
        condition += f"GROUP_ID = {group_id} AND "
    if user_id:
        condition += f"USER_ID = {user_id} AND "
    if source:
        condition += f"SOURCE = '{source.strip()}' AND "
    if target:
        condition += f"TARGET = '{target.strip()}' AND "
    cursor = cursor.execute(
        f"""
        SELECT * FROM TRANSLATE {condition.strip()[:-4]};
        """
    )
    ret = cursor.fetchall()
    connection.close()
    return ret

def to_dict(rows:list) -> dict:
    ret = {}
    for row in rows:
        session_id = f'group_{row[1]}_{row[2]}'
        if session_id not in ret:
            ret[session_id] = []
        ret[session_id].append({'source':row[3], 'target':row[4]})
    return ret