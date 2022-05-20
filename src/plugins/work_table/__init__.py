# -*- coding: utf-8 -*-
import nonebot
from nonebot import on_command, on_notice, on_message, require
from nonebot.rule import startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, GroupIncreaseNoticeEvent, MessageSegment
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, GROUP
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from os import mkdir
import json

DATA_PATH = './data'
DIR_PATH = f'{DATA_PATH}/work_table'
TABLE_PATH = f'{DIR_PATH}/work_table.json'
TRIM_PATH = f'{DIR_PATH}/trim.json'

# INITIATE
for path in [DATA_PATH, DIR_PATH]:
    try:
        mkdir(path)
    except FileExistsError:
        pass

for path in [TABLE_PATH, TRIM_PATH]:
    try: 
        with open(path, 'x') as file:
            file.write('{}')
    except FileExistsError:
        pass

with open(TABLE_PATH, 'r') as file:
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
    menu += '命令格式: /添加审核 视频文件名\n'
    menu += '命令格式: /结束审核 视频文件名\n'
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
        with open(TABLE_PATH, 'w') as file:
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
        with open(TABLE_PATH, 'w') as file:
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

# 查看待审核切片
show_trim = on_command(
    cmd = "待审核", temp=False, priority=2, block=True,
    permission=GROUP
)
@show_trim.handle()
@logger.catch
async def show_(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    with open(TRIM_PATH, 'r') as file:
        trims = json.loads(file.read())
    if group_id in trims and trims[group_id]:
        msg = '当前待审核的切片:'
        i = 0
        for trim_info in trims[group_id]:
            i = i + 1
            msg += f'\n[{i}]{trim_info[0]}, 剪辑: {trim_info[1]}'
        await show_trim.send(msg)
    else:
        await show_trim.send('当前无待审核视频')

# 添加待审核切片
add_trim = on_command(
    cmd = "添加审核",aliases={'审核', '切片审核'}, temp=False, priority=2, block=True,
    permission=GROUP
)
@add_trim.handle()
@logger.catch
async def add_(event: GroupMessageEvent):
    cmd = event.get_plaintext().split()
    if len(cmd) >= 2:
        group_id = event.get_session_id().split('_')[1]
        qq_id = event.get_session_id().split('_')[2]
        trim = event.get_plaintext().split()[1]
        if len(cmd) == 3:
            trimmer = cmd[2]
        else:
            info = await nonebot.get_bot().get_group_member_info(
                group_id=group_id, user_id=qq_id, nocache=False
            )
            trimmer = info['nickname']
            if info['card']:
                trimmer = info['card']
        with open(TRIM_PATH, 'r') as file:
            trims = json.loads(file.read())
        if group_id not in trims:
            trims[group_id] = []
        trims[group_id].append((trim, trimmer))
        with open(TRIM_PATH, 'w') as file:
            file.write(json.dumps(trims))
        await add_trim.send('待审核视频添加成功')

# 删除待审核切片
remove_trim = on_command(
    cmd = "审核完成",aliases={'审核结束', '删除审核'}, temp=False, priority=2, block=True,
    permission=GROUP
)
@remove_trim.handle()
@logger.catch
async def remove_(event: GroupMessageEvent):
    if len(event.get_plaintext().split()) == 2:
        group_id = event.get_session_id().split('_')[1]
        trim = event.get_plaintext().split()[1]
        with open(TRIM_PATH, 'r') as file:
            trims = json.loads(file.read())
        if group_id in trims:
            for trim_tuple in trims[group_id]:
                if trim == trim_tuple[0]:
                    trims[group_id].remove(trim_tuple)
                    break
        with open(TRIM_PATH, 'w') as file:
            file.write(json.dumps(trims))
        await remove_trim.send('待审核视频删除完成')
    
# 定时通知群成员审核视频
scheduler = require('nonebot_plugin_apscheduler').scheduler

# 定时推送审核提醒
@scheduler.scheduled_job('cron', hour=16, minute = 7, timezone='UTC', id='trim_remind')
@logger.catch
async def remind():
    with open(TRIM_PATH, 'r') as file:
        trims = json.loads(file.read())
    for group_id, trims_info in trims.items():
        msg = '提醒审核视频小助手提醒您, 快来和我一起审核视频:'
        i = 0
        for trim_info in trims_info:
            trim = trim_info[0]
            trimmer = trim_info[1]
            i = i + 1
            msg += f'\n[{i}]{trim}, 剪辑: {trimmer}'
        nonebot.get_bot().send_group_msg(
            group_id = group_id,
            message = msg
        )