from threading import Thread
from nonebot import logger


class ThreadPool:

    def __init__(self) -> None:
        self.__pool: dict[str, Thread] = {}

    def add_thread(self, thread: Thread):
        self.__pool[thread.name] = thread
    
    def pop_thread(self, name:str):
        return self.__pool.pop(name, None)
    
    def clean_threads(self):
        remove_list = []

        for name, thread in self.__pool.items():
            if thread.is_alive():
                return
        
            thread.join()
            remove_list.append(name)
            logger.debug(f"Thread [{thread.name}] joined.")

        for name in remove_list:
            self.__pool.pop(name)


thread_pool = ThreadPool()
