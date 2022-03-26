# -*- coding: utf-8 -*-
import nonebot
from nonebot.rule import startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, GROUP
from nonebot.permission import SUPERUSER
from os import mkdir
import json

DATA_PATH = './data'
DIR_PATH = f'{DATA_PATH}/work_table'
DB_PATH = f'{DIR_PATH}/work_table.json'

# INITIATE
for path in [DATA_PATH, DIR_PATH]:
    try:
        mkdir(path)
    except FileExistsError:
        pass
try: 
    with open(DB_PATH, 'x') as file:
        file.write('{}')
except FileExistsError:
    pass
with open(DB_PATH, 'r') as file:
    TABLES = json.loads(file.read())

# HELP
helper = nonebot.on_command(
    cmd="工作表帮助", temp=False, priority=5, block=True,
    permission=GROUP
)
@helper.handle()
async def help():
    menu = '工作表模块目前支持的功能:\n\n'
    menu += '发言以"工作表"开头调用工作表\n'
    menu += '命令格式: "/添加工作表 URL"\n'
    menu += '命令格式: "/删除工作表"'
    await helper.finish(menu)

# CALL WORK TABLE
work_table = nonebot.on_message(
    rule=startswith("工作表"), temp=False, priority=3, block=False,
    permission=GROUP
)
@work_table.handle()
async def _(event: GroupMessageEvent):
    cmd = event.get_plaintext().strip()
    if len(cmd) == 3:
        group_id = event.get_session_id().split('_')[1]
        if group_id in TABLES:
            await work_table.send(Message(TABLES[group_id]))
        else:
            await work_table.send(Message("请先添加工作表"))

# ADD WORK TABLE
add_table = nonebot.on_command(
    cmd = "添加工作表", temp=False, priority=2, block=True,
    permission=GROUP
)
@add_table.handle()
async def add(event: GroupMessageEvent):
    cmd = event.get_plaintext().split()
    group_id = event.get_session_id().split('_')[1]
    if len(cmd) == 2:
        table_url = cmd[1]
        TABLES[group_id] = table_url
        with open(DB_PATH, 'w') as file:
            file.write(json.dumps(TABLES))
        await work_table.send(Message("添加成功"))
    else:
        await work_table.send(Message("请指定工作表URL"))

# DELETE WORK TABLE
del_table = nonebot.on_command(
    cmd = "删除工作表", temp=False, priority=2, block=True,
    permission=GROUP
)
@del_table.handle()
async def delete(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    if group_id in TABLES:
        del TABLES[group_id]
        with open(DB_PATH, 'w') as file:
            file.write(json.dumps(TABLES))
        await work_table.send(Message("删除成功"))
    else:
        await work_table.send(Message("本群没有指定工作表"))