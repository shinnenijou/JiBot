# -*- coding: utf-8 -*-
from email import message
from fnmatch import translate
import aiohttp
import asyncio
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

# CONSTANT

# PROXY = nonebot.get_driver().config.dict()['proxy']
# PROXY = 'http://127.0.0.1:7890'
async def get_users_info(access_token : str, *users_name : str, ) -> list[dict[str,str]]:
    """
    从Twitter用户id获取用户相关的信息\n
    WARNING: 请求没有经过队列控制, 如果用户过多可能会超过Twitter API的请求次数限制(详见官方文档)\n
    ---
    response 字段:\n
    [str] 'id': Twitter用户唯一标识数字id, 仅后台数据使用\n
    [str] 'pinned_tweet_id': Twitter用户置顶推文的id\n
    [str] 'name': Twitter用户的自定义名称(screen name), 通常显示在主页上\n
    [str] 'username': Twitter用户的用户id, 可以由用户自定义, 通常用作前台标识用户\n
    [bool] 'protected': Twitter用户推文是否受到保护, 如果是则需要关注才能获取其推文\n
    ---
    :param access_token: Twitter Developer Platform发行的Bearer Token, 用于标识发送只读请求的APP
    :param users_name: 需要请求的Twitter用户id(@后面的部分), 接受任意数量的str
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        'expansions':'pinned_tweet_id',  # 获取置顶的推文id
        'user.fields':'protected'  # 推文是否受保护(上锁)
    } 
    async with aiohttp.ClientSession() as session:
        tasks = [_get_one_info(session, name, headers, params)\
            for name in users_name]
        users_info = await asyncio.gather(*tasks)
    return users_info

async def _get_one_info(
    session: aiohttp.ClientSession,
    user_name : str,
    headers : dict[str,str],
    params : dict[str,str],
    ) -> list[dict[str,str]]:
    user_info_api = f'https://api.twitter.com/2/users/by/username/{user_name}'
    async with session.get(
        url=user_info_api,
        headers=headers,
        params=params
        #proxy=PROXY
    ) as resp:
        try:
            data = await resp.json()
            user_info = data['data']
        except Exception as err:
            user_info = {}
            logger.error(str(err))
            logger.error(f"获取{user_name}信息失败, 请检查Access Token或网络连接设置, 并确认用户id无误")
    return user_info

async def get_users_timeline(
    access_token : str,
    users_id : list[str],
    since_tweet_ids : list[str]) -> list[dict]:
    """
    从用户数字id获取用户最新的时间线\n
    WARNING: 请求没有经过队列控制, 如果用户过多可能会超过Twitter API的请求次数限制(详见官方文档)\n
    ---
    :return 保存不同用户时间线的列表, 顺序与users_id保持一致\n
    ---
    timeline 'data'字段为包含推文基本信息字典的一个列表(无推文则无该字段)，顺序为从新到旧，字典内:\n
    [str] 'id': 该推文id()
    [str] 'text': 该推文的文本内容(推文没有文本时, 也会因为添加了附件而在本字段中包含一个该推文的链接)
    [dict] 'attachments': 该推文的附件(图片, 视频等)的信息字典(推文无附件则无此项)
    [list] 'attachments'/'media_keys': 包含各个附件id, 附件开头的数字代表了附件类型\n
    timeline 'meta'字段(必有该字段)
    [str] 'oldest_id', 'newest_id': 本次请求中最早与最新的推文id
    [str] 'result_count': 本次请求到的推文数量
    [str] 'next_token': 用于请求下一页数据的token\n
    timeline 'includes'/'media'字段为包含媒体信息字典的一个列表, 顺序与推文顺序相同从新到旧, 字典内:
    [str] 'media_key': 媒体id
    [str] 'url', 'preview_image_url': 媒体的url(图片或视频预览图)
    [str] 'type': 媒体类型
    ---
    :param access_token: Twitter Developer Platform发行的Bearer Token, 用于标识发送只读请求的APP
    :param users_id: 需要请求的Twitter用户数字id,用户id通常需要先通过get_users_info()获取
    :param since_tweet_ids : 上次更新到的推文id, 顺序与users_id保持一致
    """
    headers = {
        'Authorization' : f'BEARER {access_token}'
    }
    async with aiohttp.ClientSession() as session:
        tasks = [_get_one_timeline(session, users_id[i], headers, since_tweet_ids[i])\
            for i in range(len(users_id))]
        timeline_list = await asyncio.gather(*tasks)
    return timeline_list

async def _get_one_timeline(
    session : aiohttp.ClientSession,
    id : str,
    headers : dict[str, str],
    since_id : str = ""
    ) -> dict[str,dict]:
    timeline_api = f'https://api.twitter.com/2/users/{id}/tweets'
    params = {
        'max_results' : 5,  # 本次请求返回的最大推文数
        'exclude' : 'replies',  # 过滤掉回复
        'since_id' : since_id,  # 返回指定id之后的推文
        'tweet.fields' : 'attachments,referenced_tweets',  # 返回推文包含的附件信息(图片, 视频等),引用信息
        'expansions' : 'attachments.media_keys', # 在response中额外添加一个include字段，包含media信息
        'media.fields' : 'preview_image_url,url' # 返回推文包含的媒体预览url
    }
    if not since_id:
        del params['since_id']
    async with session.get(
        url=timeline_api,
        headers=headers,
        params=params
        #proxy=PROXY
    ) as resp:
        try:
            timeline = await resp.json()
        except Exception as err:
            timeline = {}
            logger.error(str(err))
            logger.error(f"获取{id}推文失败, 请检查Access Token或网络连接设置")
    return timeline

async def get_tweets(access_token : str, *tweet_ids : str) -> list[dict]:
    """
    根据推文id获取推文内容
    """
    tweet_api = f'https://api.twitter.com/2/tweets'
    headers = { 'Authorization' : f'BEARER {access_token}' }
    params = {
        'ids' : ','.join(tweet_id for tweet_id in tweet_ids),  # 请求的推文id
        'tweet.fields' : 'attachments,referenced_tweets',  # 返回推文包含的附件信息(图片, 视频等),引用信息
        'expansions' : 'attachments.media_keys', # 在response中额外添加一个include字段，包含media信息
        'media.fields' : 'preview_image_url,url' # 返回推文包含的媒体预览url
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url=tweet_api, headers=headers, params=params
            #proxy=PROXY
        ) as resp:
            try:
                data = await resp.json()
            except:
                data ={}
                logger.error(f'获取推文{tweet_ids}失败，请检查Access Token或网络连接设置')
    return data

def reorgnize_tweets(
    tweets_resp : dict[str,str],
    username : str
    ) -> list[dict[str,str]]:
    """
    将API返回的字典重新组织成以推文为单位的信息列表,表中一个字典就是一个推文\n
    注意: 'data', 'data'/'attachment', 'includes', 'includes'/'media'等字段都不一定会被返回\n
    'meta'字段一定会被返回, 因此主要用'meta'字段判断是否包含新推文\n
    有'attachment'或'referenced_tweets'时'text'通常会包含一段推文链接\n
    ---
    :return 最新的推文id和根据推文生成的通知信息字典的列表, 字典包含'text', 'media', 'url', 'referenced_tweets'\n
    ---
    :param tweets_resp: _get_one_timeline()返回的包含一个用户最新时间线推文内容的字典
    :param username: 用户id
    """
    tweets = []
    curr_media_index = 0
    for tweet in tweets_resp['data']:
        text = tweet['text'].replace('https://', '').replace('http://', '')
        tweet_message = {'text' : text}
        tweet_message['media_url'] = []
        tweet_message['tweet_url'] = f"https://twitter.com/{username}/status/{tweet['id']}"
        if 'attachments' in tweet:
            # 从文本中分离出推文URL(如果存在)
            # 推特短链t.co/xxxxxxxxxx 一共15个字符
            url_beg = len(text) - 15
            if text[url_beg : url_beg + 5] == 't.co/':
                tweet_message['text'] = text[:url_beg]
            # 处理media, media的顺序与推文中key顺序完全一致，可以按数量直接加入列表
            media_count = len(tweet['attachments']['media_keys'])
            for i in range(curr_media_index, curr_media_index + media_count):
                media = tweets_resp['includes']['media'][i]
                media_url = media['url'] if 'url' in media else media['preview_image_url']
                tweet_message['media_url'].append(media_url)
            curr_media_index += media_count
        if 'referenced_tweets' in tweet:
            # 从文本中分离出推文URL(如果存在), url可能会因为长度被截断, 截断则不做处理
            # BUG: 会有用户推文中原本自带的url, 因为长度正好将推特附加的url截断而被错误提取
            url_beg = len(text) - 15
            if text[url_beg : url_beg + 5] == 't.co/':
                tweet_message['tweet_url'] = text[url_beg:]
            # 处理转推的原推
            tweet_message['referenced_tweets'] = tweet['referenced_tweets']
        tweets.append(tweet_message)
    return tweets

def reorgnize_timeline(
    timeline_resp : dict[str,dict],
    username:str,
    tweet_since_id : str
    ) -> tuple[str, list[dict[str,str]]]:
    """
    在整理推文内容的基础上处理最新推文\n
    如果没有推文则返回原推文id和空列表
    """
    if not timeline_resp['meta']['result_count']:
        return tweet_since_id, []  # 如果推文字典里结果计数为0就直接返回表示为空的内容
    tweet_since_id = timeline_resp['meta']['newest_id']  # 更新最新推文id
    tweets = reorgnize_tweets(timeline_resp, username)
    return tweet_since_id, tweets

def make_message(newest_tweet:dict[str,str], name:str, 
    retweeted_tweet:dict[str,str], translate_text:str=None) -> Message:
    msg = Message([
        MessageSegment.text(f'{name} 发布了一条新推文:' + '\n---------------\n'),
        MessageSegment.text(newest_tweet['text'])
    ])
    if translate_text:
        msg.append(MessageSegment.text('\n---------------\n' + '机翻:\n' + translate_text))
    msg.append(MessageSegment.text('\n---------------\n' + newest_tweet['tweet_url']))
    for image in newest_tweet['media_url']:
            msg.append(MessageSegment.image(image))
    if retweeted_tweet:
        for image in retweeted_tweet['media_url']:
            msg.append(MessageSegment.image(image))
    return msg