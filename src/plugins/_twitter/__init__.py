# -*- coding: utf-8 -*-
import asyncio
from nonebot import on_command, on_notice
from nonebot.adapters.onebot.v11 import Message,MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, GroupDecreaseNoticeEvent
from nonebot import require
from nonebot.log import logger
import nonebot

# Import self-utils
import src.plugins._twitter.db as db
import src.plugins._twitter.twitter as twitter
import src.common.utils as utils
# CONSTANTS
ENABLE_TWEET = bool(nonebot.get_driver().config.dict().get('enable_tweet', False))
TWEET_LISTEN_INTERVAL = nonebot.get_driver().config.dict()['tweet_listen_interval']
TWEET_SOURCE = nonebot.get_driver().config.dict()['tweet_source']
TWEET_TARGET = nonebot.get_driver().config.dict()['tweet_target']
TWITTER_TOKEN = nonebot.get_driver().config.dict()['twitter_token']
# INITIATE DATABASE
db.init()
# GLOGBAL VIABLES
USER_LIST = db.get_user_list()
WHITE_LIST = db.get_white_list()

##########################
######### 包装函数 #########
async def send_msg_with_retry(bot, group_id:int, message:str):
    retry_time = 1
    send_success = False
    for i in range(retry_time):
        if send_success:
            break
        try:
            await bot.send_group_msg(
                group_id=group_id,
                message=message
            )
            send_success = True
        except:
            pass

# 请求定时任务对象scheduler
scheduler = require('nonebot_plugin_apscheduler').scheduler

# 定时请求推文
@scheduler.scheduled_job('interval', seconds=TWEET_LISTEN_INTERVAL,
    id='tweet_pusher', timezone='Asia/Shanghai')
@logger.catch
async def push_tweet():
    if not ENABLE_TWEET:
        return

    global USER_LIST
    if not USER_LIST:
        return  # 监听名单里没有目标
    bot = utils.safe_get_bot()

    if bot is None:
        return

    # 异步获取用户们的时间线
    timeline_list:list[twitter.Timeline] = await twitter.get_users_timeline(
        access_token=TWITTER_TOKEN,
        users=USER_LIST,
        white_list=WHITE_LIST
    )
    # 对每个用户的timeline进行处理
    # 索引i: 指示推特用户序号
    for i in range(len(timeline_list)):
        timeline = timeline_list[i]
        logger.debug(f'成功获取到{timeline.author_id}推文')
        tweets = timeline.tweets
        if tweets and not USER_LIST[timeline.author_id]['newest_id']:
            tweets = tweets[:1]  # 如果该用户没有过最新推文id的记录,则只推送最新一条
        # 更新最新id, 不论推文是否被推送都会在此被更新
        USER_LIST[timeline.author_id]['newest_id'] = timeline.newest_id
        db.update_newest_tweet(timeline.author_id, timeline.newest_id)
        for tweet in tweets:
            logger.success(f'成功检测到{tweet.author_username}推文更新, 准备推送')
            await tweet.translate(TWEET_SOURCE, TWEET_TARGET)
            # 发送通知
            group_list = db.get_user_groups(tweet.author_id)
            tasks = []
            for group_id, need_translate in group_list.items():
                msg = tweet.get_message(need_translate)
                task = asyncio.create_task(
                    send_msg_with_retry(bot, group_id, msg)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

# 关注推特命令(仅允许管理员操作)
follow_user = on_command('推特关注', priority=2, temp=False, block = True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@follow_user.handle()
async def follow(event:GroupMessageEvent):
    global USER_LIST
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/推特关注 推特id(不带@)"'
    if len(cmd) != 2:
        await follow_user.finish(Message(msg))
    username = cmd[1]
    # 请求命令id对应的用户
    user_info = (await twitter.get_users_info(TWITTER_TOKEN, username))[0]
    if user_info:
        user_id = user_info['id']
        name = user_info['name']
        db.add_user(user_id, username, name)
        if db.add_group_sub(user_id, group_id):
            msg = f'{name}({username})关注成功！'
            # 更新全局变量
            USER_LIST = db.get_user_list()
        else:
            msg = f'{name}({username})已经在关注列表中！'
    else:
        msg = f'用户{username}不存在, 请确认id无误'
    await follow_user.finish(Message(msg))

#取关用户(仅允许管理员操作)    
unfollow_user = on_command('推特取关', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@unfollow_user.handle()
async def unfollow(event:GroupMessageEvent):
    global USER_LIST
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/推特取关 推特id(不带@)"'
    if len(cmd) == 2:
        username = cmd[1]
        user_id, name = db.get_user_id_name(username)
        if db.delete_group_sub(user_id, group_id):
            msg = f"{name}({username})取关成功"
            # 更新全局变量
            USER_LIST = db.get_user_list()
        else:
            msg = f"{name}({username})不在本群关注列表中"
    Msg = Message(msg)
    await unfollow_user.finish(Msg)

#显示本群中的关注列表(仅允许管理员操作)  
userlist = on_command('推特关注列表', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@userlist.handle()
async def get_list(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    msg = '本群已关注以下推特:\n'
    sub_list = db.get_group_sub(group_id)
    i = 0
    for info in sub_list.values():
        i += 1
        translate_text = '开启' if info['need_translate'] else '关闭'
        msg += f"\n[{i}]{info['name']}({info['username']}) 翻译已{translate_text}"
    await userlist.finish(Message(msg))

#开启推文翻译(仅允许管理员操作)
translate_on = on_command('开启推特翻译', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@translate_on.handle()
async def on(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/开启推特翻译 推特id(不带@)"'
    if len(cmd) == 2:
        username = cmd[1]
        id, name = db.get_user_id_name(username)
        if db.translate_on(id, group_id):
            msg = f'{name}({username})开启推文翻译成功！'
        else:
            msg = f'{username}不在当前关注列表！'
    await translate_on.finish(Message(msg))

#关闭推文翻译(仅允许管理员操作)
translate_off = on_command('关闭推特翻译', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@translate_off.handle()
async def off(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/开启推特翻译 推特id(不带@)"'
    if len(cmd) == 2:
        username = cmd[1]
        id, name = db.get_user_id_name(username)
        if db.translate_off(id, group_id):
            msg = f'{name}({username})关闭推文翻译成功！'
        else:
            msg = f'{username}不在当前关注列表！'
    await translate_off.finish(Message(msg))

# 添加推特白名单
white_list_add = on_command('添加推特白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@white_list_add.handle()
async def add_white_list(event:GroupMessageEvent):
    global WHITE_LIST
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/添加推特白名单 推特id(不带@)"'
    if len(cmd) != 2:
        await white_list_add.finish(Message(msg))
    username = cmd[1]
    user_info = (await twitter.get_users_info(TWITTER_TOKEN, username))[0]
    if user_info:
        id = user_info['id']
        name = user_info['name']
        if db.add_white_list(id, username, name):
            msg = f'{name}({username}) 添加白名单成功'
            WHITE_LIST[id] = {'name':name, 'username':username}
        else:
            msg = f'{name}({username}) 已在白名单中'
    else:
        msg = f'用户{username}不存在, 请确认id无误'
    await white_list_add.finish(Message(msg))

# 移除推特白名单
white_list_remove = on_command('移除推特白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@white_list_remove.handle()
async def remove_white_list(event:GroupMessageEvent):
    global WHITE_LIST
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/移除推特白名单 推特id(不带@)"'
    if len(cmd) != 2:
        white_list_remove.finish(Message(msg))
    username = cmd[1]
    name = db.remove_white_list(username)
    if name:
        msg = f'{name}({username}) 移除白名单成功'
        WHITE_LIST = db.get_white_list()
    else:
        msg = f'{name}({username}) 不在白名单中'
    await white_list_remove.finish(Message(msg))

# 查看推特白名单
white_list = on_command('推特白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@white_list.handle()
async def get_white_list():
    msg = '以下推特用户已加入白名单:\n\n'
    msg += ', '.join(info['username'] for info in WHITE_LIST.values())
    await white_list.finish(Message(msg))

#帮助
helper = on_command('推特帮助', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@helper.handle()
async def help():
    menu = '推特模块目前支持的功能:(ID即@后的字符)\n\n'\
         + '/推特关注列表\n'\
         + '/推特关注 ID\n'\
         + '/推特取关 ID\n'\
         + '/开启推特翻译 ID\n'\
         + '/关闭推特翻译 ID\n'\
         + '/推特白名单\n'\
         + '/添加推特白名单 ID\n'\
         + '/移除推特百名单 ID'
    await helper.finish(Message(menu))

# 退群后自动删除该群关注信息
group_decrease = on_notice(priority=5)
@group_decrease.handle()
async def _(event: GroupDecreaseNoticeEvent):
    # 此处user_id是退群的qq用户
    group_id = event.get_session_id().split('_')[1]
    if event.self_id == event.user_id:
        sub_list= db.get_group_sub(group_id)
        for id in sub_list.keys():
            db.delete_group_sub(id, group_id)