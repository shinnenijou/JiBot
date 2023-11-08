#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
import src.common.utils as utils
from src.common.config import config

# Some customized operation
# make data directory
utils.Mkdir(config.get_value('data_path', 'data'))
utils.Mkdir(config.get_value('log_path', 'logs'))

# Custom your logger
# 
# from nonebot.log import logger, default_format
nonebot.logger.add(os.path.join(config.get_value('log_path', 'logs'), "{time}.log"),
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
