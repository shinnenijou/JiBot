# -*- coding: utf-8 -*-
# Python STL
import asyncio
from abc import abstractmethod, ABC
# Third-party
import nonebot
import aiohttp
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger
# Self utils
import src.plugins.twitter.utils.emojis as emojis
import src.plugins.twitter.utils.tmt as tmt

# CONSTANT
PROXY = nonebot.get_driver().config.dict()['proxy']
PROXY = None if PROXY == 'None' else PROXY

class TweetType:
    Origin = 'origin'
    Retweet = 'retweeted'
    Quote = 'quoted'
    Reply = 'replied_to'

class Tweet(ABC):
    """
    原创推文Tweet基类, 将给定信息整理并输出用于推送的Message
    """
    def __init__(self, 
        tweet_data:dict,
        user_map:dict,
        media_map:dict,
        reference_map:dict):
        """
        :params tweet_data: 一条推文的主数据, 位于API返回中的tweet.fields的'data'
        :params user_map: 从用户id映射到用户信息的字典, 需要自行从API返回中组织生成
        :params media_map: 从media_key映射到媒体url的字典, 需要自行从API返回中组织生成
        :params reference_map: 从引用推文id映射到原推详情的字典, 需要自行从API返回中组织生成
        """
        # 推文信息
        self.type:str = tweet_data['referenced_tweets'][0]['type']  # 推文类型
        self.id:str = tweet_data['id']  # 推文id
        self.author_id:str = tweet_data['author_id']  # 作者id
        self.author_name:str = user_map[self.author_id]['name']  # 作者名称
        self.author_username:str = user_map[self.author_id]['username']  # 作者用户名
        self.text:str = tweet_data['text'].strip()
        self.text_translate = ""  # 正文翻译
        self.url:str = f"https://twitter.com/{self.author_username}/status/{self.id}"  # 推文url
        self.image_urls:list[str] = []  # 推文附图
        if 'attachments' in tweet_data:
            # 推文正文, 有附件时末尾会被推特加上有本条推文的链接,
            # https://t.co/xxxxxxxxxx 共23个字符, 正文过长会被截断, 需要判断
            if self.text[-23:-18] == 'https':
                self.text = self.text[:-23].strip()
            for media_key in tweet_data['attachments']['media_keys']:
                url = media_map[media_key]['url'] if 'url' in media_map[media_key]\
                    else media_map[media_key]['preview_image_url']
                self.image_urls.append(url)

    async def translate(self, source:str, target:str) -> str:
        if self.text:
            text_list, emoji_list = emojis.split_emoji(self.text)
            translate_list = await tmt.translate(source, target, *text_list)
            self.text_translate = emojis.merge_emoji(translate_list, emoji_list).strip()
        return self.text_translate

    def get_message(self, need_translate:int) -> Message:
        # 通知抬头
        msg = f'{self.author_name} 发布了一条新推文:\n'
        # 推文正文
        msg += '--------------------\n'\
            + self.text + '\n'
        # 正文翻译
        msg += ('--------------------\n'\
            + '机翻:\n'\
            + self.text_translate + '\n')\
            * need_translate
        # 推文链接
        msg += '--------------------\n'
        msg += self.url + '\n'
        msg = Message(msg)
        # 推文附图
        for image in self.image_urls:
            msg.append(MessageSegment.image(image))
        return msg
    
class ReferenceTweet(Tweet):
    """
    存在引用行为的ReferenceTweet抽象基类
    """
    def __init__(self,
        tweet_data: dict,
        user_map: dict,
        media_map: dict,
        reference_map: dict):
        Tweet.__init__(self, tweet_data, user_map, media_map, reference_map)
        # 原推信息
        self.reference_id:str = tweet_data['referenced_tweets'][0]['id']  # 原推文id
        try:
            referenced_tweet:dict = reference_map[self.reference_id]
            self.reference_author_id:str = referenced_tweet['author_id']  # 原推作者id
            self.reference_author_name:str = user_map[self.reference_author_id]['name']  # 原推作者名称
            self.reference_author_username:str = user_map[self.reference_author_id]['username']  # 原推作者用户名
            self.reference_text:str = referenced_tweet['text'].strip()  # 原推正文
            if 'attachments' in referenced_tweet and self.reference_text[-23:-18] == 'https':
                self.reference_text = self.reference_text[:-23].strip()
            self.reference_text_translate = ""  # 原推正文翻译
            self.reference_image_urls:list[str] = []  # 原推附图, 此处暂时留空
        except Exception as err:
            logger.error(f'Twitter: {err}')
            self.reference_author_id = ''
            
    
    async def translate(self, source: str, target: str) -> str:
        await Tweet.translate(self, source, target)
        if self.reference_text:
            text_list, emoji_list = emojis.split_emoji(self.reference_text)
            translate_list = await tmt.translate(source, target, *text_list)
            self.reference_text_translate = emojis.merge_emoji(translate_list, emoji_list)
        return self.reference_text_translate

    @abstractmethod
    def get_message(self, need_translate: int) -> Message:
        """
        构造Message供bot发送的抽象虚函数, 子类各自实现
        """
class Retweet(ReferenceTweet):
    """
    转推子类Retweet类, 将给定信息整理并输出用于推送的Message
    NOTE: 正文会复读一遍原推的正文. 原推的图片也会出现在本条信息中, 可以直接从media_map获取
    NOTE: 原推的图片将在Tweet构造函数中当作本推文的图片保存
    """
    def __init__(self,
        tweet_data: dict,
        user_map: dict,
        media_map: dict,
        reference_map: dict):

        ReferenceTweet.__init__(self, tweet_data, user_map, media_map, reference_map)
        self.reference_text = ""  # 将原推正文删除, 避免重复翻译
        
    def get_message(self, need_translate: int) -> Message:
        # 通知抬头
        msg = f'{self.author_name} 转发了 {self.reference_author_name} 的一条推文:\n'
        # 推文正文
        msg += '--------------------\n'\
            + self.text + '\n'
        # 正文翻译
        msg += ('--------------------\n'\
            + '机翻:\n'\
            + self.text_translate + '\n')\
            * need_translate
        # 推文链接
        msg += '--------------------\n'
        msg += self.url + '\n'
        msg = Message(msg)
        # 推文附图
        for image in self.image_urls:
            msg.append(MessageSegment.image(image))
        for image in self.reference_image_urls:
            msg.append(MessageSegment.image(image))
        return msg

class Reply(ReferenceTweet):
    """
    子类Reply类, 将给定信息整理并输出用于推送的Message
    NOTE: 本条回复和原推都可能带有图片, 子类构造函数只处理原推带的图片(再次请求进行获取)
    NOTE: 本条回复的图片将在Tweet构造函数中当作本推文的图片保存
    """
    def __init__(self,
        tweet_data: dict,
        user_map: dict,
        media_map: dict,
        reference_map: dict):

        ReferenceTweet.__init__(self, tweet_data, user_map, media_map, reference_map)
        # 暂时策略: 回复类型的推文不推送原推图片
    
    def get_message(self, need_translate: int) -> Message:
        # 通知抬头
        msg = f'{self.author_name} 回复了 {self.reference_author_name} 的一条推文:\n'
        # 推文正文
        msg += '--------------------\n'\
            + self.text + '\n'
        # 正文翻译
        msg += ('--------------------\n'\
            + '机翻:\n'\
            + self.text_translate + '\n')\
            * need_translate
        # 原推正文
        msg += '--------------------\n'\
            + '引用原文:\n'\
            + self.reference_text + '\n'
        # 原推翻译
        msg += ('--------------------\n'\
            + '机翻:\n'\
            + self.reference_text_translate + '\n')\
            * need_translate
        # 推文链接
        msg += '--------------------\n'
        msg += self.url + '\n'
        msg = Message(msg)
        # 推文附图
        for image in self.image_urls:
            msg.append(MessageSegment.image(image))
        for image in self.reference_image_urls:
            msg.append(MessageSegment.image(image))
        return msg
    
class Quote(ReferenceTweet):
    """
    子类Quote类, 将给定信息整理并输出用于推送的Message
    NOTE: 本条引用和原推都可能带有图片, 子类构造函数只处理原推带的图片(再次请求进行获取)
    NOTE: 本条回复的图片将在Tweet构造函数中当作本推文的图片保存
    """

    def __init__(self,
        tweet_data: dict,
        user_map: dict,
        media_map: dict,
        reference_map: dict):

        ReferenceTweet.__init__(self, tweet_data, user_map, media_map, reference_map)
        # 暂时策略: 引用类型的推文不推送原推图片
        # 引用时正文末尾会被推特加上引用推文的链接, 并且此链接会和因图片带来的链接叠加
        # https://t.co/xxxxxxxxxx 共23个字符, 正文过长会被截断, 需要判断
        if self.text[-23:-18] == 'https':
            self.text = self.text[:-23].strip()

    def get_message(self, need_translate: int) -> Message:
        # 通知抬头
        msg = f'{self.author_name} 引用了 {self.reference_author_name} 的一条推文:\n'
        # 推文正文
        msg += '--------------------\n'\
            + self.text + '\n'
        # 正文翻译
        msg += ('--------------------\n'\
            + '机翻:\n'\
            + self.text_translate + '\n')\
            * need_translate
        # 原推正文
        msg += '--------------------\n'\
            + '引用原文:\n'\
            + self.reference_text + '\n'
        # 原推翻译
        msg += ('--------------------\n'\
            + '机翻:\n'\
            + self.reference_text_translate + '\n')\
            * need_translate
        # 推文链接
        msg += '--------------------\n'
        msg += self.url + '\n'
        msg = Message(msg)
        # 推文附图
        for image in self.image_urls:
            msg.append(MessageSegment.image(image))
        for image in self.reference_image_urls:
            msg.append(MessageSegment.image(image))
        return msg
        
CLASS_MAP = {
    TweetType.Origin: Tweet,
    TweetType.Retweet: Retweet,
    TweetType.Reply: Reply,
    TweetType.Quote: Quote
}        
class Timeline:
    """
    将API的数据整理为推文列表, 会过滤掉白名单以外的回复, 转推
    """
    def __init__(self, user_id: str, newest_id: str, resp: dict,
        white_list: dict[str,dict]):
        """
        :param resp: 推特API返回的json数据
        """
        self.tweets:list[Tweet] = []
        self.author_id = user_id
        self.newest_id = newest_id
        if not resp or not resp['meta']['result_count']:
            return
        # 时间线主数据
        self.tweets_data = resp['data']
        self.newest_id = resp['meta']['newest_id']
        # 用户映射表
        self.user_map = {}
        for user in resp['includes']['users']:
            self.user_map[user['id']] = user
        # 媒体映射表
        self.media_map = {}
        if 'media' in resp['includes']:
            for media in resp['includes']['media']:
                self.media_map[media['media_key']] = media
        # 引用映射表
        self.reference_map = {}
        if 'tweets' in resp['includes']:
            for reference in resp['includes']['tweets']:
                self.reference_map[reference['id']] = reference
        # 整理推文
        for tweet_data in self.tweets_data:
            if 'referenced_tweets' not in tweet_data:
                tweet_data['referenced_tweets'] = [{'type': TweetType.Origin}]
            tweet_type = tweet_data['referenced_tweets'][0]['type']
            tweet = CLASS_MAP[tweet_type](
                tweet_data, self.user_map, self.media_map,self.reference_map)
            if tweet.type == TweetType.Origin or tweet_type == TweetType.Quote\
                or tweet.reference_author_id in white_list:
                self.tweets.append(tweet)

async def get_users_info(access_token: str, *usernames: str, ) -> list[dict[str,str]]:
    """
    从Twitter用户id获取用户信息, 返回信息字典的列表, 不存在该用户将会返回空字典\n
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
            for name in usernames]
        users_info = await asyncio.gather(*tasks)
        await session.close()
    return users_info

async def _get_one_info(
    session: aiohttp.ClientSession,
    username: str,
    headers: dict[str,str],
    params: dict[str,str],
    ) -> list[dict[str,str]]:
    user_info_api = f'https://api.twitter.com/2/users/by/username/{username}'
    async with session.get(
        url=user_info_api,
        headers=headers,
        params=params,
        proxy=PROXY
    ) as resp:
        try:
            data = await resp.json()
            user_info = data['data']
        except Exception as err:
            user_info = {}
            logger.error(f'Twitter: 请求{username}信息时发生错误: {err}')
    return user_info

async def get_users_timeline(
    access_token: str,
    users: dict[str,dict],
    white_list: list[str]
    ) -> list[Timeline]:
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
    timeline 'includes'/'in_replied_user_id'包含推文回复的用户id
    ---
    :param access_token: Twitter Developer Platform发行的Bearer Token, 用于标识发送只读请求的APP
    :param users: 需要请求的Twitter用户群字典, 索引为id, value包含name, username, newest_id
    """
    headers = {
        'Authorization': f'BEARER {access_token}'
    }
    async with aiohttp.ClientSession() as session:
        tasks = []
        for user_id, info in users.items():
            task = asyncio.create_task(
                _get_one_timeline(session,user_id,headers,info['newest_id'],white_list)
            )
            tasks.append(task)
        timeline_list = await asyncio.gather(*tasks)
    return timeline_list

async def _get_one_timeline(
    session: aiohttp.ClientSession,
    user_id: str,
    headers: dict[str, str],
    newest_id: str,
    white_list: list[str]
    ) -> Timeline:
    timeline_api = f'https://api.twitter.com/2/users/{user_id}/tweets'
    params = {
        'max_results': 10,  # 本次请求返回的最大推文数
        #'exclude': 'replies',  # 过滤掉回复
        'since_id': newest_id,  # 返回指定id之后的推文
        'tweet.fields': 'attachments,referenced_tweets',  # 返回推文包含的附件信息(图片, 视频等),引用信息
        'expansions': 'attachments.media_keys,referenced_tweets.id.author_id', # 在response中额外添加一个include字段
        'media.fields': 'preview_image_url,url' # 返回推文包含的媒体预览url
    }
    if not newest_id:
        del params['since_id']
    async with session.get(
        url=timeline_api,
        headers=headers,
        params=params,
        proxy=PROXY
    ) as resp:
        try:
            tweets_data = await resp.json()
        except Exception as err:
            logger.error(f"获取{user_id}时间线发生错误: {err}")
            tweets_data = {}
        timeline = Timeline(user_id, newest_id, tweets_data, white_list)
    return timeline

async def get_tweet_media(access_token: str, tweet_id: str) -> list[str]:
    """
    根据推文id获取推文媒体内容, 主要用于获取原推图片
    """
    tweet_api = f'https://api.twitter.com/2/tweets/{tweet_id}'
    headers = { 'Authorization': f'BEARER {access_token}' }
    params = {
        'tweet.fields': 'attachments',  # 返回推文包含的附件信息(图片, 视频等),引用信息
        'expansions': 'attachments.media_keys', # 在response中额外添加一个include字段，包含media信息
        'media.fields': 'preview_image_url,url',  # 返回推文包含的媒体预览url
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url=tweet_api,headers=headers,params=params,proxy=PROXY) as resp:
            image_urls = []
            try:
                tweet_data = await resp.json()
                if 'includes' in tweet_data:
                    for image in tweet_data['includes']['media']:
                        url = image['url'] if 'url' in image else image['preview_image_url']
                        image_urls.append(url)
            except Exception as err:
                logger.error(f'获取推文{tweet_id}发生错误: {err}')
        await session.close()
    return image_urls
