from threading import Thread, Event
from nonebot import logger


class ThreadPool:

    def __init__(self) -> None:
        self.__pool: dict[str, Thread] = {}
        self.__recording_status: dict[str, Event] = {}

    def add_thread(self, thread: Thread):
        self.__pool[thread.name] = thread
    
    def pop_thread(self, thread_name: str):
        return self.__pool.pop(thread_name, None)
    
    def clean_threads(self):
        remove_list = []

        for name, thread in self.__pool.items():
            if thread.is_alive():
                return
        
            thread.join()
            remove_list.append(name)
            logger.debug(f"Thread [{thread.name}] joined.")

        for name in remove_list:
            self.pop_thread(name)

    def is_recording(self, streamer_name: str):
        return streamer_name in self.__recording_status and self.__recording_status[streamer_name].is_set()

    def add_recording(self, streamer_name: str):
        self.__recording_status[streamer_name] = Event()
        return self.__recording_status[streamer_name]

task_manager = ThreadPool()
