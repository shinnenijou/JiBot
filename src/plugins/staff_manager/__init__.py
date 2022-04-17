# -*- coding: utf-8 -*-
# Python STL
import asyncio
# Third-party lib
import nonebot
from nonebot import on_command, on_notice
from nonebot.params import ArgPlainText
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, GROUP_MEMBER
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment, GroupIncreaseNoticeEvent
# self-utils
import src.plugins.staff_manager.db as db
import src.plugins.staff_manager.utils.occupation as occupation

# Initiate Database
db.init()
####################
##### 命令帮助 ######
helper = on_command(cmd='人员管理帮助', temp=False, priority=2, block=True,
    permission=GROUP_ADMIN|GROUP_MEMBER|GROUP_OWNER|SUPERUSER)
@helper.handle()
async def show_menu():
    menu= '人员管理模块包含以下功能:\n'\
        + '\n(群管理)命令格式: "/人员统计"'\
        + '\n(群管理)命令格式: "/人员查询 职位名称(或人员qq号)"'\
        + '\n(群管理)命令格式: "/来点(召唤, 有无)职位名称"'\
        + '\n(所有群员)命令格式: "/人员注册 名称 职位"'\
        + '\n(所有群员)命令格式: "/人员注销 名称"'
#        + '\n(bot管理)命令格式: "/注册字幕组 字幕组名"'\
#        + '\n(bot管理)命令格式: "/强制注册字幕组 群号 字幕组名"'\
#        + '\n(bot管理)命令格式: "/注销字幕组"'\
#        + '\n(bot管理)命令格式: "/强制人员注册 群号 qq号 职位"'
#        + '\n(bot管理)命令格式: "/强制人员注销 群号 qq号"'
    await helper.finish(Message(menu))

####################
##### 人员统计 ######
staff_stat = on_command(cmd='人员统计', temp=False, priority=2, block=True,
    permission=GROUP_OWNER|GROUP_ADMIN|SUPERUSER)
@staff_stat.handle()
async def stat(event: GroupMessageEvent):
    """
    统计群内各个职位人次
    """
    group_id = event.get_session_id().split('_')[1]
    if not db.is_registered(group_id):
        await staff_stat.finish(Message('本群还未注册为字幕组群'))
    staff_list = db.get_all_staff(group_id)
    occupation_stastic = {}
    for occupatio_name, mask in occupation.MASKS.items():
        cnt = 0
        for staff_info in staff_list.values():
            if staff_info['occupation'] & mask:
                cnt += 1
        occupation_stastic[occupatio_name] = cnt
    msg = f'本群在册共{len(staff_list.keys())}人, 职位人次分布如下:\n(输入/人员查询 职位名称 以查询具体人员名单)'
    i = 1
    for occupation_name, cnt in occupation_stastic.items():
        msg += f'\n[{i}]{occupation_name}: {cnt}人'
        i += 1
    await staff_stat.finish(Message(msg))

show_staff = on_command(cmd='人员查询', temp=False, priority=2, block=True,
    permission=GROUP_OWNER|GROUP_ADMIN|SUPERUSER)
@show_staff.handle()
async def show(event: GroupMessageEvent):
    """
    查询某个职位的人员名单, 或查询某个人员的职位
    """
    group_id = event.get_session_id().split('_')[1]
    if not db.is_registered(group_id):
        await show_staff.finish(Message('本群还未注册为字幕组群'))
    cmd = event.get_plaintext().split()
    msg = '命令错误, 请按照"/人员查询 职位名称(或人员qq号)"输入命令\n职位名称严格按照以下输入: '\
        + '剪辑, 时轴, 翻译, 校对, 美工, 特效, 后期, 皮套, 画师, 同传'
    if len(cmd) != 2 or (cmd[1] not in occupation.MASKS and not cmd[1].isdigit()):
        await show_staff.finish(Message(msg))
    # 查询某位人员
    if cmd[1].isdigit():
        qq_id = int(cmd[1])
        staff_info = db.get_one_staff(group_id, qq_id)
        if staff_info:
            occupations = occupation.get_occupations(staff_info[qq_id]['occupation'])
            msg = f'{staff_info[qq_id]["name"]}({qq_id})当前职位为: '
            msg += ', '.join(_ for _ in occupations)
        else:
            msg = '查无此人'
    # 查询某职位所有人员
    else:
        staff_list = db.get_occupation_staff(group_id, occupation.MASKS[cmd[1]])
        i = 1
        msg = f'{cmd[1]}职位共{len(staff_list.keys())}人:'
        for staff_info in staff_list.values():
            msg += f"\n[{i}]{staff_info['name']}"
            i += 1
    await show_staff.finish(Message(msg))

####################
#### 组群注册管理 ####
register_group = on_command(cmd='注册字幕组', temp=False, priority=2, block=True,
    permission=SUPERUSER)
@register_group.handle()
async def register(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令错误, 请按照"/注册字幕组 字幕组名"格式输入'
    if len(cmd) != 2:
        await register_group.finish(Message(msg))
    group_name = cmd[1]
    if db.add_group(group_id, group_name):
        msg = f'{group_name}({group_id})注册成功'
    else:
        msg = f'{group_name}({group_id})已存在'
    await register_group.finish(Message(msg))

force_register_group = on_command(cmd='强制注册字幕组', temp=False, priority=1, block=True,
    permission=SUPERUSER)
@force_register_group.handle()
async def register(event: GroupMessageEvent):
    cmd = event.get_plaintext().split()
    group_id = int(cmd[1])
    group_name = cmd[2]
    if db.add_group(group_id, group_name):
        msg = f'{group_name}({group_id})注册成功'
    else:
        msg = f'{group_name}({group_id})已存在'
    await force_register_group.finish(Message(msg))

delete_group = on_command(cmd='注销字幕组', temp=False, priority=2, block=True,
    permission=SUPERUSER)
@delete_group.handle()
async def delete(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    if not db.is_registered(group_id):
        await delete_group.finish(Message('本群还未注册为字幕组群'))
@delete_group.got('comfirm', '该操作将清楚已注册人员名单并不可撤回。你确认要执行此操作?(确认/取消)')
async def comfirm_delete(event: GroupMessageEvent):
    comfirmation = event.get_plaintext().strip()
    if comfirmation != '确认':
        await delete_group.finish('该操作已取消')
    group_id = event.get_session_id().split('_')[1]
    if db.delete_group(group_id):
        msg = f'{group_id}删除成功'
    else:
        msg = f'{group_id}未注册'
    await delete_group.finish(Message(msg))

####################
#### 人员注册管理 ####
register_staff = on_command(cmd='人员注册', temp=False, priority=2, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|GROUP_MEMBER|SUPERUSER)
@register_staff.handle()
async def register(event: GroupMessageEvent):
    group_id = int(event.get_session_id().split('_')[1])
    qq_id = int(event.get_session_id().split('_')[2])
    # 检查群是否已注册
    if not db.is_registered(group_id):
        await register_staff.finish(Message('本群还未注册为字幕组群'))
    # 检查输入规范
    occupations = event.get_plaintext().split()[1:]
    msg = '命令错误, 请按照"/人员注册 职位名称"输入命令\n职位名称严格按照以下输入: '\
        + '剪辑, 时轴, 翻译, 校对, 美工, 特效, 后期, 皮套, 画师, 同传; 多个职位以空格隔开'
    for occupation_name in occupations:
        if not occupation_name in occupation.MASKS:
            await register_staff.finish(Message(msg))
    # 获取人员qq名称
    info = await nonebot.get_bot().get_group_member_info(
        group_id=group_id, user_id=qq_id, nocache=False
    )
    name = info['nickname']
    if info['card']:
        name = info['card']
    # 计算职位
    occupation_sum = 0
    for occupation_name in occupations:
        occupation_sum += occupation.MASKS[occupation_name]
    # 添加人员
    if db.add_occupation(group_id, qq_id, name, occupation_sum):
        curr = db.get_one_staff(group_id, qq_id)
        occupations = []
        for occupation_name, mask in occupation.MASKS.items():
            if curr[qq_id]['occupation'] & mask:
                occupations.append(occupation_name)
        msg = f'{name}({qq_id})职位更新成功, 当前职位为: '
    else:
        msg = f'{name}({qq_id})注册成功, 当前职位为: '
    msg += ', '.join(occupation_name for occupation_name in occupations)
    await register_staff.finish(Message(msg))

remove_staff = on_command(cmd='人员注销', temp=False, priority=2, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|GROUP_MEMBER|SUPERUSER)
@remove_staff.handle()
async def remove(event: GroupMessageEvent):
    group_id = int(event.get_session_id().split('_')[1])
    qq_id = int(event.get_session_id().split('_')[2])
    if not db.is_registered(group_id):
        await remove_staff.finish(Message('本群还未注册为字幕组群'))
    # 检查输入规范
    occupations = event.get_plaintext().split()[1:]
    msg = '命令错误, 请按照"/人员注销 职位名称"输入命令\n职位名称严格按照以下输入: '\
        + '剪辑, 时轴, 翻译, 校对, 美工, 特效, 后期, 皮套, 画师, 同传; 多个职位以空格隔开'
    for occupation_name in occupations:
        if not occupation_name in occupation.MASKS:
            await register_staff.finish(Message(msg))
    # 获取人员qq名称
    info = await nonebot.get_bot().get_group_member_info(
        group_id=group_id, user_id=qq_id, nocache=False
    )
    name = info['nickname']
    if info['card']:
        name = info['card']
    # 计算职位
    occupation_sum = 0
    for occupation_name in occupations:
        occupation_sum += occupation.MASKS[occupation_name]
    # 注销职位
    if db.remove_occupation(group_id, qq_id, occupation_sum):
        curr = db.get_one_staff(group_id, qq_id)
        occupations = []
        for occupation_name, mask in occupation.MASKS.items():
            if curr[qq_id]['occupation'] & mask:
                occupations.append(occupation_name)
        if occupations:
            msg = f'{name}({qq_id})职位更新成功, 当前职位: '
            msg += ', '.join(occupation_name for occupation_name in occupations)
        else:
            db._remove_staff(group_id, qq_id)
            msg = f'{name}({qq_id})已成功注销所有职位'
    else:
        msg = f'{name}({qq_id})注册信息不存在'
    await remove_staff.finish(Message(msg))

force_register_staff = on_command(cmd='强制人员注册', temp=False, priority=2, block=True,
    permission=SUPERUSER)
@force_register_staff.handle()
async def remove(event: GroupMessageEvent):
    group_id = int(event.get_plaintext().split()[1])
    qq_id = int(event.get_plaintext().split()[2])
    # 检查群是否已注册
    if not db.is_registered(group_id):
        await register_staff.finish(Message('本群还未注册为字幕组群'))
    # 检查输入规范
    occupations = event.get_plaintext().split()[3:]
    msg = '命令错误, 请按照"/人员注册 职位名称"输入命令\n职位名称严格按照以下输入: '\
        + '剪辑, 时轴, 翻译, 校对, 美工, 特效, 后期, 皮套, 画师, 同传; 多个职位以空格隔开'
    for occupation_name in occupations:
        if not occupation_name in occupation.MASKS:
            await register_staff.finish(Message(msg))
    # 获取人员qq名称
    info = await nonebot.get_bot().get_group_member_info(
        group_id=group_id, user_id=qq_id, nocache=False
    )
    name = info['nickname']
    if info['card']:
        name = info['card']
    # 计算职位
    occupation_sum = 0
    for occupation_name in occupations:
        occupation_sum += occupation.MASKS[occupation_name]
    # 添加人员
    if db.add_occupation(group_id, qq_id, name, occupation_sum):
        curr = db.get_one_staff(group_id, qq_id)
        occupations = []
        for occupation_name, mask in occupation.MASKS.items():
            if curr[qq_id]['occupation'] & mask:
                occupations.append(occupation_name)
        msg = f'{name}({qq_id})职位更新成功, 当前职位为: '
    else:
        msg = f'{name}({qq_id})注册成功, 当前职位为: '
    msg += ', '.join(occupation_name for occupation_name in occupations)
    await register_staff.finish(Message(msg))

force_remove_staff = on_command(cmd='强制人员注销', temp=False, priority=2, block=True,
    permission=SUPERUSER)
@force_remove_staff.handle()
async def remove(event: GroupMessageEvent):
    group_id = int(event.get_plaintext().split()[1])
    qq_id = int(event.get_plaintext().split()[2])
    if not db.is_registered(group_id):
        await remove_staff.finish(Message('本群还未注册为字幕组群'))
    # 检查输入规范
    occupations = event.get_plaintext().split()[3:]
    msg = '命令错误, 请按照"/人员注销 职位名称"输入命令\n职位名称严格按照以下输入: '\
        + '剪辑, 时轴, 翻译, 校对, 美工, 特效, 后期, 皮套, 画师, 同传; 多个职位以空格隔开'
    for occupation_name in occupations:
        if not occupation_name in occupation.MASKS:
            await register_staff.finish(Message(msg))
    # 获取人员qq名称
    info = await nonebot.get_bot().get_group_member_info(
        group_id=group_id, user_id=qq_id, nocache=False
    )
    name = info['nickname']
    if info['card']:
        name = info['card']
    # 计算职位
    occupation_sum = 0
    for occupation_name in occupations:
        occupation_sum += occupation.MASKS[occupation_name]
    # 注销职位
    if db.remove_occupation(group_id, qq_id, occupation_sum):
        curr = db.get_one_staff(group_id, qq_id)
        occupations = []
        for occupation_name, mask in occupation.MASKS.items():
            if curr[qq_id]['occupation'] & mask:
                occupations.append(occupation_name)
        if occupations:
            msg = f'{name}({qq_id})职位更新成功, 当前职位: '
            msg += ', '.join(occupation_name for occupation_name in occupations)
        else:
            db._remove_staff(group_id, qq_id)
            msg = f'{name}({qq_id})已成功注销所有职位'
    else:
        msg = f'{name}({qq_id})注册信息不存在'
    await remove_staff.finish(Message(msg))

####################
#### 人员管理应用 ####
at_staff = on_command(cmd='来点', aliases={'召唤', '有无'}, temp=False, priority=2, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@at_staff.handle()
async def at(event: GroupMessageEvent):
    occupation_name = event.get_plaintext().strip()[3:].strip()
    group_id = event.get_session_id().split('_')[1]
    if not db.is_registered(group_id):
        await at_staff.finish(Message('该群还未注册为字幕组群'))
    msg = '命令错误, 请按照"/来点(召唤, 有无)职位名称"输入命令\n职位名称严格按照以下输入: '\
        + '剪辑, 时轴, 翻译, 校对, 美工, 特效, 后期, 皮套, 画师, 同传'
    if not occupation_name in occupation.MASKS:
        await at_staff.finish(Message(msg))
    staff_list = db.get_occupation_staff(group_id, occupation.MASKS[occupation_name])
    msg = Message()
    for qq_id in staff_list.keys():
        msg.append(MessageSegment.at(qq_id))
    await at_staff.finish(msg)
