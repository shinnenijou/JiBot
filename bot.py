#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from src.common.utils import Mkdir

# Some customized operation
# make data directory
Mkdir("data")
Mkdir("logs")

# Custom your logger
# 
# from nonebot.log import logger, default_format
nonebot.logger.add("./logs/{time}.log",
            rotation="00:00",
            diagnose=False,
            level="INFO",
            retention='14 days')

# You can pass some keyword args config to init function
nonebot.init()
#app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

nonebot.load_builtin_plugins("single_session")
nonebot.load_builtin_plugins("echo")

# Please DO NOT modify this file unless you know what you are doing!
# As an alternative, you should use command `nb` or modify `pyproject.toml` to load plugins
nonebot.load_from_toml("pyproject.toml")

# Modify some config / config depends on loaded configs



if __name__ == "__main__":
    nonebot.logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run()
