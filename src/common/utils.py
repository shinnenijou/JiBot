import os
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, GroupIncreaseNoticeEvent, MessageSegment


class Singleton:
    __instance = None

    def __new__(cls, *argv, **kwarg):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance


def Mkdir(path: str):
    "Create a directary if not exists"
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


def Touch(path: str, orig_text: str = "") -> bool:
    "Create a new file if not exists"
    try:
        file = open(path, 'r')
        file.close()
    except FileNotFoundError:
        file = open(path, 'w')
        file.write(orig_text)
        file.close()


def get_group_id(event: GroupMessageEvent) -> str:
    return str(event.get_session_id().split('_')[1])


def get_cmd_param(event: GroupMessageEvent) -> list[str]:
    return event.get_plaintext().strip().split()[1:]


def get_cmd(event: GroupMessageEvent) -> str:
    return event.get_plaintext().strip().split()[0]
