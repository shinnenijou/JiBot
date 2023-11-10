import os
import sqlite3 as dblib

import nonebot
from nonebot import logger

class SQL:
    def __init__(self):
        self.__sections = []

    def __str__(self) -> str:
        return ' '.join(_ for _ in self.__sections) + ';'

    def add(self, *args) -> None:
        self.__sections.extend(args)
    

class DBClient:

    def __init__(self) -> None:
        self.__path = os.path.join(nonebot.get_driver().config.dict().get('data_path', 'data'), 'data.db')
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

    def commit(self) -> None:
        self.__conn.commit()

    def select(self, prop: str, table: str, **kwargs) -> list:
        sql = SQL()

        sql.add('SELECT', prop, 'FROM', table)
        sql.add('WHERE', '1=1')

        for key, value in kwargs.items():
            sql.add('AND', f'{key}={self.__normalize(value)}')

        try:
            result = self.__cur.execute(str(sql)).fetchall()
        except Exception as e:
            result = []
            logger.error(str(e))

        return result

    def exists(self, table: str) -> bool:
        result = self.select('count(*)', 'sqlite_master', type='table', name=table)
        return result[0][0] != 0

    def create(self, table: str, primary: str | None = None, **kwargs) -> bool:
        if len(kwargs) == 0:
            return False

        sql = SQL()
        sql.add('CREATE', 'TABLE', table)

        sql.add('(')

        sections = []
        for key, value in kwargs.items():
            section = [key, value, 'not null']

            if primary is not None and key == primary:
                section.append('primary key')

            sections.append(' '.join(_ for _ in section)) 

        sql.add(', '.join(_ for _ in sections))
        sql.add(')')

        try:
            self.__cur.execute(str(sql)).fetchall()
            self.commit()
            return True
        except Exception as e:
            logger.error(str(e))
            return False
    
    def drop(self, table:str) -> bool:
        sql = SQL()
        sql.add('DROP', 'TABLE', table)

        try:
            self.__cur.execute(str(sql))
            self.commit()
            return True
        except Exception as e:
            logger.error(str(e))
            return False
    
    def insert(self, table: str, **kwargs) -> bool:
        if len(kwargs) == 0:
            return False

        sql = SQL()
        sql.add('INSERT INTO', table)
        
        sql.add()
        sql.add('(', ', '.join(key for key in kwargs.keys()), ')')
        sql.add('VALUES(', ', '.join(self.__normalize(value) for value in kwargs.values()), ')')

        try:
            self.__cur.execute(str(sql))
            self.commit()
            return True
        except Exception as e:
            logger.error(str(e))
            return False

    def update(self, table: str, set: dict, **kwargs) -> bool:
        if len(set) == 0:
            return False

        sql = SQL()

        sql.add('UPDATE', table)

        sql.add('SET')
        sql.add(', '.join(f'{key}={self.__normalize(value)}' for key, value in set.items()))
        
        sql.add('WHERE', '1=1')

        for key, value in kwargs.items():
            sql.add('AND', f'{key}={self.__normalize(value)}')
        
        try:
            self.__cur.execute(str(sql))
            self.commit()
            return True
        except Exception as e:
            logger.error(str(e))
            return False

    def delete(self, table: str, **kwargs) -> bool:
        sql = SQL()
        sql.add('DELETE FROM', table, 'WHERE', '1=1')

        for key, value in kwargs.items():
            sql.add('AND', f'{key}={self.__normalize(value)}')

        try:
            self.__cur.execute(str(sql))
            self.commit()
            return True
        except Exception as e:
            logger.error(str(e))
            return False