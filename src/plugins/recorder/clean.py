import os
import psutil
import time

from nonebot import logger, get_driver

from src.common.utils import parse_datetime

class Cleaner:

    def __init__(self, reserve_size: int, expire_time: int) -> None:
        self.__reserve_size = reserve_size
        self.__expire_time = expire_time

    @property
    def reserve_size(self):
        return self.__reserve_size

    @property
    def expire_time(self):
        return self.__expire_time

    def clean(self, path: str, prior_dir: str = ''):
        if not os.path.isdir(path):
            return
        
        if self.disk_enough():
            return

        prior_path = os.path.join(path, prior_dir)
        self.clean_path(prior_path)

        if self.disk_enough():
            return
        
        dir_list = os.listdir(path)
        
        if prior_dir in dir_list:
            dir_list.remove(prior_dir)

        for dir in dir_list:
            self.clean_path(os.path.join(path, dir))

            if self.disk_enough():
                break

    def disk_enough(self):
        disk_usage = psutil.disk_usage("/")
        return disk_usage.free > self.reserve_size 

    def clean_path(self, path: str):
        """NOT RECURSIVE"""

        if not os.path.isdir(path):
            return
        
        if self.disk_enough():
            return

        file_list = os.listdir(path)
        file_list.sort(key=parse_datetime)

        for filename in file_list:
            if not os.path.isfile(os.path.join(path, filename)):
                continue

            create_time = parse_datetime(filename)

            if create_time == 0:
                logger.error(f"Unknown filename format: {filename}")
                continue 

            now_time = int(time.time())

            if now_time - create_time > self.expire_time:
                os.remove(os.path.join(path, filename))
                logger.info(f"Remove old record file: {filename}.")

            if self.disk_enough():
                break


cleaner = Cleaner(
   reserve_size=get_driver().config.dict().get('disk_reserve_size', 50 * 1024 * 1024 * 1024),
   expire_time=24 * 60 * 60
)