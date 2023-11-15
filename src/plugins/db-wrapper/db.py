import os
import sqlite3 as dblib

import nonebot
from nonebot import logger

from .sql import SQL


class DBClient:

    def __init__(self) -> None:
        self.__path = os.path.join(nonebot.get_driver(
        ).config.dict().get('data_path', 'data'), 'data.db')
        self.__conn = dblib.connect(self.__path)
        self.__cur = self.__conn.cursor()

    @property
    def path(self) -> str:
        return self.__path

    @staticmethod
    def __normalize(value):
        if isinstance(value, str):
            return f'"{value}"'

        if isinstance(value, int):
            return str(value)

        return value

    ################ Basic Operation ##############

    def commit(self) -> None:
        self.__conn.commit()

    def try_excute(self, sql: SQL) -> list:
        try:
            result = self.__cur.execute(str(sql)).fetchall()
            return True, result
        except Exception as e:
            result = []
            logger.error(str(e))
            return False, result
        
    def excute(self, sql: SQL) -> bool:
        status, _ = self.try_excute(sql)

        if status:
            self.commit()
        
        return status

    ################ Simple Wrappers ##############

    def select(self, attr: str, table: str, **kwargs) -> tuple[bool, list]:
        sql = SQL()

        sql.Select(attr).From(table)
        sql.Where('1=1')

        for key, value in kwargs.items():
            sql.And(f'{key}={self.__normalize(value)}')

        _, result = self.try_excute(sql)

        return result 

    def exists(self, table: str) -> bool:
        result = self.select('*', 'sqlite_master', type='table', name=table)
        return len(result) > 0

    def create(self, table: str, primary: str | None = None, **kwargs) -> bool:
        if len(kwargs) == 0:
            return False

        sql = SQL()
        sql.Create(table)

        for key, value in kwargs.items():
            section = [key, value, 'not null']

            if primary is not None and key == primary:
                section.append('primary key')

            sql.add(' '.join(_ for _ in section), ',')

        sql.EndValues(len(kwargs))

        return self.excute(sql)

    def drop(self, table: str) -> bool:
        sql = SQL()
        sql.Drop(table)

        return self.excute(sql)

    def insert(self, table: str, **kwargs) -> bool:
        if len(kwargs) == 0:
            return False

        sql = SQL()
        sql.InsertTo(table)

        for key in kwargs.keys():
            sql.add(key, ',')

        sql.EndValues(len(kwargs.keys()))

        sql.Values()
        
        for value in kwargs.values():
            sql.add(self.__normalize(value), ',')

        sql.EndValues(len(kwargs.values()))

        return self.excute(sql)

    def update(self, table: str, set: dict, **kwargs) -> bool:
        if len(set) == 0:
            return False

        sql = SQL()

        sql.Update(table)

        sql.Set()

        for key, value in set.items():
            sql.add(f'{key}={self.__normalize(value)}', ',')
        
        sql.EndValues(len(set))

        sql.Where('1=1')

        for key, value in kwargs.items():
            sql.And(f'{key}={self.__normalize(value)}')

        return self.excute(sql)

    def delete(self, table: str, **kwargs) -> bool:
        sql = SQL()
        sql.Delete(table).Where('1=1')

        for key, value in kwargs.items():
            sql.And(f'{key}={self.__normalize(value)}')

        return self.excute(sql)


db = DBClient()
