# -*- coding: utf-8 -*-
import sqlite3
from sqlite3 import OperationalError
from os import mkdir
from sre_constants import SUCCESS
from typing import Tuple

DATA_PATH = './data'
WISHLIST_DIR_PATH = f'{DATA_PATH}/wishlist_listener'
DB_PATH = f'{WISHLIST_DIR_PATH}/wishlists.db'

def init() -> None:
    try:
        mkdir(DATA_PATH)
    except FileExistsError:
        pass
    try:
        mkdir(WISHLIST_DIR_PATH)
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

def get_users_on(group_id : int = None) -> Tuple[str,...]:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor = cursor.execute(
            f"""
            select target_name from wishlists where group_id={group_id};
            """
        )
        ret = list(name[0] for name in cursor.fetchall())
    return ret

def get_all_users() -> set:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor = cursor.execute(
            f"""
            select target_name from wishlists where id!=0;
            """
        )
        ret = set(name[0] for name in cursor.fetchall())
    return ret

def get_groups_on(name : str = None) -> list[int]:
    """
    获取订阅给定名称愿望单的群
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor = cursor.execute(
            f"""
            select group_id from wishlists where target_name='{name}';
            """
        )
        ret = list(group[0] for group in cursor.fetchall())
    return ret

def get_items(name : str) -> list[str]:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor = cursor.execute(
            f"""
            select commodity from {name} where id!=0;
            """
        )
        ret = list(item[0] for item in cursor.fetchall())
    return ret

def get_url(name : str) -> str:
    """
    注意: 原则上一个名称只能对应一个URL, 重复的将会在add的阶段被阻止
    可以存在多个名称对应一个URL
    """
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor = cursor.execute(
            f"""
            select url from wishlists where target_name='{name}';
            """
        )
    return cursor.fetchone()[0]

def add_listen(group_id : int, name : str, url : str) -> bool:
    success = True
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor = cursor.execute(f"select url from wishlists where target_name='{name}';")
        url_list = list(url[0] for url in cursor.fetchall())
        if url_list and url not in url_list:
            success = False
        else:
            cursor = cursor.execute(
                f"""
                select id from wishlists where group_id={group_id} and target_name='{name}';
                """
            )
            if not cursor.fetchall():
                cursor = cursor.execute("select max(id) from wishlists;")
                id = cursor.fetchone()[0] + 1
                try:
                    cursor.execute(
                        f"""
                        insert into wishlists values({id}, {group_id}, '{name}', '{url}');
                        """
                    )
                    connection.commit()
                except:
                    success = False
            else:
                success = False
    _add_table(name)
    return success

def delete_listen(group_id : int, name : str) -> bool:
    success = True
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        try:
            cursor = cursor.execute(
                f"""
                delete from wishlists where group_id={group_id} and target_name='{name}';
                """
            )
            cursor = cursor.execute(f"select count(*) from wishlists where target_name='{name}';")
            count = cursor.fetchone()[0]
            if not count:
                cursor = cursor.execute(f"drop table {name};")
            connection.commit()
        except OperationalError:
            success = False
        
    return success

def delete_group(group_id : int) -> bool:
    success = True
    target_list = get_users_on(group_id)
    for name in target_list:
        delete_listen(group_id, name)
    return success

def update_commodities(name : str, new_items : list[str], buyed_items : list[str]) -> bool:
    success = True
    with sqlite3.connect(DB_PATH) as connection:
        try:
            cursor = connection.cursor()
            for item in buyed_items:
                cursor = cursor.execute(
                    f"""
                    delete from {name} where commodity='{item}';
                    """
                )
            cursor = cursor.execute(f'select max(id) from {name};')
            id = cursor.fetchone()[0] + 1
            for item in new_items:
                cursor = cursor.execute(
                    f"""
                    insert into {name} values({id}, '{item}');
                    """
                )
                id += 1
            connection.commit()
        except OperationalError:
            success = False
    return success

def _add_table(table_name : str) -> bool:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        success = True
        try:
            cursor = cursor.execute(
                f"""
                create table {table_name}(
                    id int primary key not null,
                    commodity varchar(255) not null
                );
                """
            )
            cursor.execute(
                f"""
                insert into {table_name} values(0, 'null');
                """
            )
            connection.commit()
        except OperationalError:
            success = False
    return success

def _delete_table(table_name : str) -> bool:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        success = True
        try:
            cursor.execute(
                f"""
                drop table {table_name};
                """
            )
        except OperationalError:
            success = False
    return success

def _show_table(table_name : str) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            select * from {table_name};
            """
        )
        ret = cursor.fetchall()
    return ret