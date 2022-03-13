# -*- coding: utf-8 -*-
import asyncio
from email import message
from nonebot import on_command, on_notice
from nonebot.adapters.onebot.v11 import Message,MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, GroupDecreaseNoticeEvent
from nonebot import require
from nonebot.log import logger
import nonebot

# Import self-utils
import src.plugins.twitter.tmt as tmt
import src.plugins.twitter.utils as utils
import src.plugins.twitter.db as db
import src.plugins.twitter.twitter as twitter
# CONSTANTS
TWEET_LISTEN_INTERVAL = nonebot.get_driver().config.dict()['tweet_listen_interval']
TWEET_SOURCE = nonebot.get_driver().config.dict()['tweet_source']
TWEET_TARGET = nonebot.get_driver().config.dict()['tweet_target']
TWITTER_TOKEN = nonebot.get_driver().config.dict()['twitter_token']
# INITIATE DATABASE
db.init()
# GLOGBAL VIABLES
ID_LIST, USERNAME_LIST, NAME_LIST, NEWEST_TWEET_LIST = db.get_user_list()
WHITE_LIST, _, _ = db.get_white_list()

# 请求定时任务对象scheduler   
scheduler = require('nonebot_plugin_apscheduler').scheduler

# 定时请求推文
@scheduler.scheduled_job('interval', seconds=TWEET_LISTEN_INTERVAL, id='tweet')
async def tweet():
    global NEWEST_TWEET_LIST
    if not ID_LIST:
        return  # 监听名单里没有目标
    bot = nonebot.get_bot()
    logger.success('开始获取新推文')
    timeline_list = await twitter.get_users_timeline(
        access_token=TWITTER_TOKEN,
        users_id=ID_LIST,
        since_tweet_ids=NEWEST_TWEET_LIST
    )
    for i in range(len(timeline_list)):
        newest_tweet_id, tweets = twitter.reorgnize_timeline(
            timeline_list[i], USERNAME_LIST[i], NEWEST_TWEET_LIST[i], WHITE_LIST
        )
        if tweets and not NEWEST_TWEET_LIST[i]:
            tweets = tweets[:1]  # 如果该用户没有过最新推文id的记录,则只推送最新一条
        NEWEST_TWEET_LIST[i] = newest_tweet_id
        db.update_newest_tweet(ID_LIST[i], newest_tweet_id)
        for tweet in tweets:
            # 初始化两个引用变量
            referenced_tweet = {}
            referenced_translate = ""
            if tweet['type'] == 'quoted' or tweet['type'] == 'replied_to':
                logger.success('存在引用推文，开始获取原引用')
                referenced_tweet = await twitter.get_tweets(
                    TWITTER_TOKEN, tweet['referenced_id'])
                # 引用翻译
                referenced_tweet = twitter.reorgnize_tweets(
                    referenced_tweet, USERNAME_LIST[i], WHITE_LIST)[0]
                text_list, emoji_list = utils.split_emoji(referenced_tweet['text'])
                text_list = await tmt.translate(TWEET_SOURCE, TWEET_TARGET, *text_list)
                referenced_translate = utils.merge_emoji(text_list, emoji_list)
            # 正文翻译
            text_list, emoji_list = utils.split_emoji(tweet['text'])
            text_list = await tmt.translate(TWEET_SOURCE, TWEET_TARGET, *text_list)
            main_translate = utils.merge_emoji(text_list, emoji_list)
            # 发送通知
            group_list, translate_on_list = db.get_user_groups(ID_LIST[i])
            messages = []
            for j in range(len(group_list)):
                messages.append(twitter.make_message(
                    NAME_LIST[i],
                    tweet,
                    referenced_tweet,
                    main_translate * translate_on_list[j],
                    referenced_translate * translate_on_list[j]
                    )
                )
                print(messages[i])
            await asyncio.gather(*[
                bot.send_group_msg(group_id=group_list[i], message=messages[i])\
                    for i in range(len(group_list))
            ])

# 关注推特命令(仅允许管理员操作)
follow_user = on_command('推特关注', priority=2, temp=False, block = True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@follow_user.handle()
async def follow(event:GroupMessageEvent):
    global ID_LIST, USERNAME_LIST, NAME_LIST, NEWEST_TWEET_LIST
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
            # 更新数据库
            db.update_newest_tweet(user_id, '')  # 初始的最新推文id为空字符串
            ID_LIST, USERNAME_LIST, NAME_LIST, NEWEST_TWEET_LIST = db.get_user_list()
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
    group_id = event.get_session_id().split('_')[1]
    cmd = event.get_plaintext().split()
    msg = '命令格式错误, 请按照命令格式: "/推特取关 推特id(不带@)"'
    if len(cmd) == 2:
        username = cmd[1]
        user_id, name = db.get_user_id_name(username)
        if db.delete_group_sub(user_id, group_id):
            msg = f"{name}({username})取关成功"
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
    _, name_list, username_list, translate_list = db.get_group_sub(group_id)
    for i in range(len(name_list)):
        translate_text = '开启' if translate_list[i] else '关闭'
        msg += f'\n{name_list[i]}({username_list[i]})  翻译已{translate_text}'
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
            WHITE_LIST, _, _ = db.get_white_list()
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
        WHITE_LIST, _, _ = db.get_white_list()
    else:
        msg = f'{name}({username}) 不在白名单中'
    await white_list_remove.finish(Message(msg))

# 查看推特白名单
white_list = on_command('推特白名单', priority=2, temp=False, block=True,
    permission=SUPERUSER)
@white_list.handle()
async def get_white_list():
    _, username_list, name_list = db.get_white_list()
    msg = '以下推特用户已加入白名单:\n'
    for i in range(len(username_list)):
        msg += f'\n[{i + 1}]{name_list[i]}({username_list[i]})'
    print(msg)
    await white_list.finish(Message(msg))

#帮助
helper = on_command('推特帮助', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@helper.handle()
async def help():
    menu = '目前支持的功能:(推特ID即@后面的名称)\n\n'\
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
        id_list, _, _, _ = db.get_group_sub(group_id)
        for id in id_list:
            db.delete_group_sub(id, group_id)