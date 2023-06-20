# -*- coding: utf-8 -*-
import nonebot
from nonebot import on_command, on_notice, on_message, require
from nonebot.rule import startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, GroupIncreaseNoticeEvent, MessageSegment
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, GROUP
from nonebot.log import logger
from ...common import utils
from .work_table import Table
import json
from ...common import config

TRIM_PATH = config.make_data_path('work_table/trim.json')
TABLE = Table('work_table.json')

# INITIATE
utils.Touch(TRIM_PATH, '{}')

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
    menu += '命令格式: /审核 视频文件名\n'
    menu += '命令格式: /审核完成 视频文件名\n'
    menu += '命令格式: "/删除工作表"'
    await helper.finish(menu)

# CALL WORK TABLE
work_table = on_message(
    rule=startswith("工作表"), temp=False, priority=3, block=False,
    permission=GROUP
)
@work_table.handle()
async def _(event: GroupMessageEvent):
    group_id = utils.get_group_id(event)
    obj = TABLE.get(group_id)
    if obj:
        await work_table.finish(Message(obj))
    else:
        await work_table.finish(Message("请先添加工作表"))

# ADD WORK TABLE
add_table = on_command(
    cmd = "添加工作表", temp=False, priority=2, block=True,
    permission=GROUP
)
@add_table.handle()
async def add(event: GroupMessageEvent):
    cmd = utils.get_cmd_param(event)
    group_id = utils.get_group_id(event)
    if len(cmd) < 1:
        await work_table.finish(Message("请指定工作表URL"))

    if TABLE.add(group_id, cmd[0]):
        await work_table.finish(Message("添加成功"))
    else:
        await work_table.finish(Message("已存在工作表，覆盖请使用/更新工作表 指令"))

# DELETE WORK TABLE
del_table = on_command(
    cmd = "删除工作表", temp=False, priority=2, block=True,
    permission=GROUP
)
@del_table.handle()
async def delete(event: GroupMessageEvent):
    group_id = utils.get_group_id(event)
    if TABLE.delete(group_id):
        await work_table.finish(Message("删除成功"))
    else:
        await work_table.finish(Message("本群没有指定工作表"))

# UPDATE WORK TABLE
update_table = on_command(
    cmd = "更新工作表", temp=False, priority=2, block=True,
    permission=GROUP
)
@update_table.handle()
async def update(event: GroupMessageEvent):
    group_id = utils.get_group_id(event)
    if TABLE.update(group_id):
        await work_table.finish(Message("更新成功"))
    else:
        await work_table.finish(Message("不存在工作表, 添加请使用/添加工作表 指令"))

# Welcome The New
at_new = on_notice(temp=False, priority=2, block=True)
@at_new.handle()
async def welcome(event: GroupIncreaseNoticeEvent):
    group_id = utils.get_group_id(event)
    new_id = event.get_user_id()
    msg = Message([
        MessageSegment.at(new_id),
        MessageSegment.text('进群请修改群名片为: 职务-名字, 并查看群公告内及工作表首页的组内须知。'),
        MessageSegment.text(f'\n工作表: {TABLE.get(group_id)}')
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
@scheduler.scheduled_job('cron', hour=11, timezone='UTC', id='trim_remind')
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
        await nonebot.get_bot().send_group_msg(
            group_id = group_id,
            message = msg
        )