# -*- coding: utf-8 -*-
import nonebot
from nonebot import on_command, on_notice, on_message
from nonebot.rule import startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, GroupIncreaseNoticeEvent, MessageSegment
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
helper = on_command(
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
work_table = on_message(
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
add_table = on_command(
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
del_table = on_command(
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

# Welcome The New
at_new = on_notice(temp=False, priority=2, block=True)
@at_new.handle()
async def welcome(event: GroupIncreaseNoticeEvent):
    group_id = event.get_session_id().split('_')[1]
    new_id = event.get_user_id()
    msg = Message([
        MessageSegment.at(new_id),
        MessageSegment.text('进群请修改群名片为: 职务-名字, 并查看群公告内及工作表首页的组内须知。'),
        MessageSegment.text(f'\n工作表: {TABLES[group_id]}')
    ])
    await at_new.finish(msg)