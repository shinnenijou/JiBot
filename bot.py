#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

# You can pass some keyword args config to init function
nonebot.init()
#app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

# make data directory
data_dir = nonebot.get_driver().config.dict().get('data_dir', 'data')
if not os.path.exists(data_dir):
    os.mkdir(data_dir)

log_path = nonebot.get_driver().config.dict().get('log_path', 'logs')
if not os.path.exists(log_path):
    os.mkdir(log_path)

nonebot.load_builtin_plugins("single_session")
nonebot.load_builtin_plugins("echo")

# Please DO NOT modify this file unless you know what you are doing!
# As an alternative, you should use command `nb` or modify `pyproject.toml` to load plugins
nonebot.load_from_toml("pyproject.toml")

# Modify some config / config depends on loaded configs


# Custom your logger
# 
# from nonebot.log import logger, default_format
nonebot.logger.add(os.path.join(log_path, "{time}.log"),
            rotation="00:00",
            diagnose=False,
            level="INFO",
            retention='14 days')

if __name__ == "__main__":
    nonebot.logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run()