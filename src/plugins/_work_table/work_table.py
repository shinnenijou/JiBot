import os
import nonebot
from ...common.utils import Singleton, Mkdir, Touch
import json

class Table(Singleton):
    def __init__(self, filename:str) -> None:
        self.__dir = os.path.join(nonebot.get_driver().config.dict().get('data_dir', 'data'), 'work_table')
        Mkdir(self.__dir)
        self.__path = self.__dir + '/' + filename
        Touch(self.__path, '{}')
        self.__data = dict()

        self.__load_from_db()


    def __load_from_db(self):
        with open(self.__path, 'r') as file:
            self.__data = json.loads(file.read())

    def __write_to_db(self):
        with open(self.__path, 'w') as file:
            file.write(json.dumps(self.__data))

    def add(self, group_id:str, obj:str) -> bool:
        "Return True if successfully add a new obj, False if exists obj for the group"
        if group_id in self.__data.keys():
            return False
        
        self.__data[group_id] = obj
        self.__write_to_db()
        return True

    def delete(self, group_id:str) -> bool:
        "Return True if successfully delete obj for the group, False if not exists obj"
        if group_id not in self.__data.keys():
            return False
        
        del self.__data[group_id]
        self.__write_to_db()
        return True

    def get(self, group_id:str) -> str:
        if group_id not in self.__data.keys():
            return ""
        
        return self.__data[group_id]

    def update(self, group_id:str, obj:str) -> bool:
        "Return True if successfully update obj for the group, False if not exists obj"
        if group_id not in self.__data.keys():
            return False
        
        self.__data[group_id] = obj
        self.__write_to_db()
        return True