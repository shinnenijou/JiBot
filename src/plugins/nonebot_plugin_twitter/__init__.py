# -*- coding: utf-8 -*-
import asyncio
from email import message
from nonebot import on_command, on_notice
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message,MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, GroupDecreaseNoticeEvent
from nonebot import require
from nonebot.log import logger
import nonebot

# Import self-utils
import src.plugins.nonebot_plugin_twitter.tmt as tmt
import src.plugins.nonebot_plugin_twitter.utils as utils
import src.plugins.nonebot_plugin_twitter.db as db
import src.plugins.nonebot_plugin_twitter.twitter as twitter
# CONSTANTS
TWEET_LISTEN_INTERVAL = nonebot.get_driver().config.dict()['tweet_listen_interval']
TWEET_SOURCE = nonebot.get_driver().config.dict()['tweet_source']
TWEET_TARGET = nonebot.get_driver().config.dict()['tweet_target']
TWITTER_TOKEN = nonebot.get_driver().config.dict()['twitter_token']
# INITIATE DATABASE
db.init()
# GLOGBAL VIABLES
ID_LIST, USERNAME_LIST, NAME_LIST, NEWEST_TWEET_LIST = db.get_all_users()

# 请求定时任务对象scheduler   
scheduler = require('nonebot_plugin_apscheduler').scheduler

# 定时请求推文
@scheduler.scheduled_job('interval', seconds=TWEET_LISTEN_INTERVAL, id='tweet')
async def tweet():
    global NEWEST_TWEET_LIST
    bot = nonebot.get_bot()
    logger.success('开始获取新推文')
    timeline_list = await twitter.get_users_timeline(
        access_token=TWITTER_TOKEN,
        users_id=ID_LIST,
        since_tweet_ids=NEWEST_TWEET_LIST
    )
    for i in range(len(timeline_list)):
        newest_tweet_id, tweets = twitter.reorgnize_timeline(
            timeline_list[i], USERNAME_LIST[i], NEWEST_TWEET_LIST[i]
        )
        if tweets and not NEWEST_TWEET_LIST[i]:  # 如果该用户没有过最新推文id的记录,则只推送最新一条
            tweets = tweets[:1]
        NEWEST_TWEET_LIST[i] = newest_tweet_id
        db.update_newest_tweet(ID_LIST[i], newest_tweet_id)
        for tweet in tweets:
            retweeted_tweet = {}
            if 'referenced_tweets' in tweet:
                logger.success('存在引用推文，开始获取原引用')
                retweeted_tweet = await twitter.get_tweets(
                    TWITTER_TOKEN, tweet['referenced_tweets'][0]['id'])
                retweeted_tweet = twitter.reorgnize_tweets(retweeted_tweet, USERNAME_LIST[i])[0]
            text_list, emoji_list = utils.split_emoji(tweet['text'])
            text_list = await tmt.translate(TWEET_SOURCE, TWEET_TARGET, *text_list)
            translate_text = utils.merge_emoji(text_list, emoji_list)
            group_list, translate_on_list = db.get_all_groups(ID_LIST[i])
            messages = []
            for j in range(len(group_list)):
                print(group_list)
                messages.append(twitter.make_message(tweet, NAME_LIST[i],
                    retweeted_tweet, translate_text * translate_on_list[j]))
            await asyncio.gather(*[
                bot.send_group_msg(group_id=group_list[i], message=messages[i])\
                for i in range(len(group_list))
            ])

    # # 立即获取最新的一条推文
            # timeline = (await twitter.get_users_timeline(TWITTER_TOKEN, [user_id], ['']))[0]
            # newest_tweet_id, tweets = twitter.reorgnize_timeline(timeline, username, '')
            # # 如果新推文有引用则获取引用推文内容
            # newest_tweet = tweets[0]
            # retweeted_tweet = {}
            # if 'referenced_tweets' in newest_tweet:
                # retweeted_tweet = await twitter.get_tweets(
                #     TWITTER_TOKEN, newest_tweet['referenced_tweets']['id'])
            #     retweeted_tweet = twitter.reorgnize_tweets(retweeted_tweet, username)
            # text_list, emoji_list = utils.split_emoji(newest_tweet['text'])
            # text_list = await tmt.translate(TWEET_SOURCE, TWEET_TARGET, *text_list)
            # translate_text = utils.merge_emoji(text_list, emoji_list)
            # msg = twitter.make_message(newest_tweet, name,
            #     retweeted_tweet, translate_text)



#     if model.Empty():
#         return #数据库关注列表为空，无事发生
#     schedBot = nonebot.get_bot()
#     users = model.GetUserList()
#     tweet_id,data = await twitter.get_latest_tweet(users[tweet_index][2],config.token)
#     if tweet_id == '' or users[tweet_index][3] == tweet_id:
#         tweet_index += 1
#         return #最新推文id和上次收录的一致(说明并未更新)
#     logger.info('检测到 %s 的推特已更新'%(users[tweet_index][1]))
#     model.UpdateTweet(users[tweet_index][0],tweet_id) #更新数据库的最新推文id
#     text,source_text,media_list,retweet_name=twitter.get_tweet_details(data) #读取tweet详情
#     ###### AUTHOR: Shinnen #######
#     text_list, emoji_list = utils.split_emoji(
#         source_text.replace('http://', '').replace('https://',''))
#     translate = await tmt.translate(TWEET_SOURCE, TWEET_TARGET, *text_list)
#     translate = utils.merge_emoji(translate, emoji_list)
#     ##############################
#     media = ''
#     for item in media_list:
#         media += MessageSegment.image(item)+'\n'
#     cards = model.GetALLCard(users[tweet_index][0])
#     for card in cards:
#         if card[1] == 1:#是群聊
#             if model.IsNotInCard(retweet_name,card[0]): #如果是转推，已经推送过则不再推送
#                 if card[2] == 1:#需要翻译
#                     await schedBot.call_api('send_msg',**{
#                         'message':f'{text}\r\n机翻：\r\n{translate}' + media,
#                             'group_id':card[0]
#                     })
#                 else:#不需要翻译
#                     await schedBot.call_api('send_msg',**{
#                             'message':text+media,
#                             'group_id':card[0]
#                     })
#             else:
#                 logger.info(f'QQ群({card[0]})重复推文过滤')
#         else:#私聊
#             if model.IsNotInCard(retweet_name,card[0]):
#                 if card[2] == 1:#需要翻译
#                     await schedBot.call_api('send_msg',**{
#                         'message':text+translate+media,
#                         'user_id':card[0]
#                     })
#                 else:
#                     await schedBot.call_api('send_msg',**{
#                         'message':text+media,
#                         'user_id':card[0]
#                     })
#             else:
#                 logger.info(f'QQ群({card[0]})重复推文过滤')
#     tweet_index += 1
    
# 关注推特命令(仅允许管理员操作)
adduser = on_command('推特关注', priority=2, temp=False, block = True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@adduser.handle()
async def add(event:GroupMessageEvent, args:Message=CommandArg()):
    global ID_LIST, USERNAME_LIST, NAME_LIST, NEWEST_TWEET_LIST
    group_id = event.get_session_id().split('_')[1]
    msg = '命令格式错误, 请按照命令格式: "/推特关注 推特id(不带@)"'
    if len(args) != 1:
        await adduser.finish(Message(msg))
    username = args[0].data['text']
    # 请求命令id对应的用户
    user_info = (await twitter.get_users_info(TWITTER_TOKEN, username))[0]
    if user_info:
        user_id = user_info['id']
        name = user_info['name']
        db.add_new_user(user_id, username, name)
        if db.add_group_sub(user_id, group_id):
            msg = f'{name}({username})关注成功！'
            # 更新数据库
            db.update_newest_tweet(user_id, '')  # 初始的最新推文id为空字符串
            ID_LIST, USERNAME_LIST, NAME_LIST, NEWEST_TWEET_LIST = db.get_all_users()
            
        else:
            msg = f'{name}({username})已经在关注列表中！'
    else:
        msg = f'用户{username}不存在, 请确认id无误'
    await adduser.finish(Message(msg))

#取关用户(仅允许管理员操作)    
deleteuser = on_command('推特取关', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@deleteuser.handle()
async def delete(event:GroupMessageEvent, args:Message=CommandArg()):
    group_id = event.get_session_id().split('_')[1]
    msg = '命令格式错误, 请按照命令格式: "/推特取关 推特id(不带@)"'
    if len(args) == 1:
        username = args[0].data['text']
        user_id, name = db.get_id_n_name(username)
        if db.delete_group_sub(user_id, group_id):
            msg = f"{name}({username}取关成功)"
        else:
            msg = f"{name}({username}不在本群关注列表中)"
    Msg = Message(msg)
    await adduser.finish(Msg)

#显示本群中的关注列表(仅允许管理员操作)  
userlist = on_command('推特关注列表', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER,)
@userlist.handle()
async def get_list(event: GroupMessageEvent):
    group_id = event.get_session_id().split('_')[1]
    msg = '用户名(推特ID):\n'
    id_list, name_list, username_list = db.get_group_users(group_id)
    for i in range(len(name_list)):
        msg += f'\n{name_list[i]}({username_list[i]})'
    await userlist.finish(Message(msg))

#开启推文翻译(仅允许管理员操作)
translate_on = on_command('开启推特翻译', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER)
@translate_on.handle()
async def on(event: GroupMessageEvent, args:Message=CommandArg()):
    group_id = event.get_session_id().split('_')[1]
    msg = '命令格式错误, 请按照命令格式: "/开启推特翻译 推特id(不带@)"'
    if len(args) == 1:
        username = args[0].data['text']
        id, name = db.get_id_n_name(username)
        if db.translate_on(id, group_id):
            msg = f'{name}({username})开启推文翻译成功！'
        else:
            msg = f'{username}不在当前关注列表！'
    await translate_on.finish(Message(msg))

#关闭推文翻译(仅允许管理员操作)
translate_off = on_command('关闭推特翻译', priority=2, temp=False, block=True,
    permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER,)
@translate_off.handle()
async def off(event: GroupMessageEvent, args:Message=CommandArg()):
    group_id = event.get_session_id().split('_')[1]
    msg = '命令格式错误, 请按照命令格式: "/开启推特翻译 推特id(不带@)"'
    if len(args) == 1:
        username = args[0].data['text']
        id, name = db.get_id_n_name(username)
        if db.translate_off(id, group_id):
            msg = f'{name}({username})关闭推文翻译成功！'
        else:
            msg = f'{username}不在当前关注列表！'
    await translate_off.finish(Message(msg))

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
         + '/关闭推特翻译 ID'
    await helper.finish(Message(menu))

# 退群后自动删除该群关注信息
group_decrease = on_notice(priority=5)
@group_decrease.handle()
async def _(event: GroupDecreaseNoticeEvent):
    # 此处user_id是退群的qq用户
    group_id = event.get_session_id().split('_')[1]
    if event.self_id == event.user_id:
        id_list, username_list, name_list = db.get_group_users(group_id)
        for id in id_list:
            db.delete_group_sub(id, group_id)