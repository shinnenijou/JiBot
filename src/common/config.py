import nonebot
from nonebot import logger


class ConfigWarpper:

    def __init__(self) -> None:
        self.__config:dict = nonebot.get_driver().config.dict()

    def get_int(self, _option: str, _fallback: int = 0) -> int:
        ret = _fallback
        value:str = self.__config.get(_option.lower(), _fallback)

        if value.isnumeric(value):
            ret = int(value)
        else:
            logger.error(f"{_option} config type error")

        return ret

    def get_float(self, _option: str, _fallback: float = 0) -> float:
        ret = _fallback
        value:str = self.__config.get(_option.lower(), _fallback)

        if value.isnumeric(value):
            ret = float(value)
        else:
            logger.error(f"{_option} config type error")

        return ret
    
    def get_value(self, _option: str, _fallback: str = '') -> str:
        return self.__config.get(_option.lower(), _fallback) 

config = ConfigWarpper()
