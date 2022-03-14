# -*- coding: utf-8 -*-
import json
import asyncio
from abc import ABC, abstractmethod
from bilibili_api import comment, Credential, user
import src.plugins.bilibili.utils.tmt as tmt
import src.plugins.bilibili.utils.emojis as emojis
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment


# CONSTANT
class DynamicType:
    REPOST = 1
    IMAGEDYNAMIC = 2
    TEXTDYNAMIC = 4
    VIDEODYNAMIC = 8
    COLUMNDYNAMIC = 64

# TODO COLUMN DYNAMIC
REPLY_MAP = {
    DynamicType.REPOST : comment.ResourceType.DYNAMIC,
    DynamicType.TEXTDYNAMIC : comment.ResourceType.DYNAMIC,
    DynamicType.IMAGEDYNAMIC : comment.ResourceType.DYNAMIC_DRAW,
    DynamicType.VIDEODYNAMIC : comment.ResourceType.VIDEO
}

class Dynamic(ABC):
    """
    动态基类
    """
    def __init__(self, dy_info: dict, credential:Credential):
        """
        基类实现一部分通用信息的构造, 在所有动态中这些信息的key都是固定的
        """
        self.credential = credential
        self.type = dy_info['desc']['type']
        self.author_id = dy_info['desc']['uid']
        self.author_name = dy_info['desc']['user_profile']['info']['uname']
        self.dynamic_id = dy_info['desc']['dynamic_id']
        self.timestamp = dy_info['desc']['timestamp']
        # 初始化一个空的翻译文本
        self.translate_text = ""
        # 无emoji的动态也将包含self.emoji_urls方便统一处理
        self.emoji_urls = {}
        if 'emoji_info' in dy_info['display']:
            for emoji in dy_info['display']['emoji_info']['emoji_details']:
                self.emoji_urls[emoji['text']] = emoji['url']
        # 无图的动态也将包含self.image_urls方便统一处理
        self.image_urls = []
        if 'item' in dy_info['card'] and 'pictures' in dy_info['card']['item']:
            for pic in dy_info['card']['item']['pictures']:
                self.image_urls.append(pic['img_src'])

    @abstractmethod
    def make_message(self, need_translate:int):
        """
        构造Message供bot发送的抽象虚函数, 子类各自实现
        """

    async def translate(self, source:str, target:str):
        """
        子类通用的翻译接口, 将动态翻译为指定的语言。返回翻译后文本的同时将文本保存在类内。
        """
        source_list, emoji_list = emojis.split_emoji(self.text)
        target_list = await tmt.translate(source, target, *source_list)
        self.translate_text = emojis.merge_emoji(target_list, emoji_list)
        return self.translate_text

    async def comment(self, text:str) -> None:
        """
        子类通用发送动态评论接口
        """
        return await comment.send_comment(
            text=text,
            oid=self.reply_id,
            type_=REPLY_MAP[self.type],
            credential=self.credential
        )

class Repost(Dynamic):
    """
    转发动态Repost类, 从返回的response中提取动态相关的信息并组织成Message
    Note: 转发不能带图, 原推可能带图
    """
    def __init__(self, dy_info:dict, credential:Credential):
        """
        :param dy_info: API返回的动态信息字典
        """
        # 本动态内容
        Dynamic.__init__(self, dy_info, credential)
        self.url = f'https://t.bilibili.com/{self.dynamic_id}'
        self.reply_id = dy_info['desc']['dynamic_id']
        self.text = dy_info['card']['item']['content']
        self.emoji_urls = {}
        # 上一条动态
        self.pre_dynamic_id = self.dynamic_id = dy_info['desc']['pre_dy_id']
        # 原动态内容
        origin_card = json.loads(dy_info['card']['origin'])
        self.orig_author_uid = dy_info['card']['origin_user']['info']['uid']
        self.orig_author_name = dy_info['card']['origin_user']['info']['uname']
        self.orig_dynamic_id = dy_info['desc']['orig_dy_id']
        self.orig_image_urls = []
        ## Text or Image
        if 'item' in origin_card:
            # Image
            if 'pictures' in origin_card['item']:
                self.orig_type = DynamicType.IMAGEDYNAMIC
                self.orig_text = origin_card['item']['description']
                for pic in origin_card['item']['pictures']:
                    self.orig_image_urls.append(pic['img_src'])
            # Text or Repost
            else:
                self.orig_type = DynamicType.TEXTDYNAMIC
                self.orig_text = origin_card['item']['content']
        ## Video
        elif 'desc' in origin_card:
            self.orig_type = DynamicType.VIDEODYNAMIC
            self.orig_video_title = origin_card['title']
            self.orig_video_desc = origin_card['desc']
            self.orig_text = ""
            if 'dynamic' in origin_card:
                self.orig_text = origin_card['dynamic']
            self.orig_image_urls.append(origin_card['pic'])
        ## Column
        elif 'summary' in origin_card:
            self.orig_type = DynamicType.COLUMNDYNAMIC
            self.orig_column_title = origin_card['title']
            self.orig_column_summary = origin_card['summary']
        # emoji, 共有    
        self.orig_emoji_urls = {}
        if 'origin' in dy_info['display'] and 'emoji_info' in dy_info['display']['origin']:
            for emoji in dy_info['display']['origin']['emoji_info']['emoji_details']:
                self.orig_emoji_urls[emoji['text']] = emoji['url']

    def make_message(self, need_translate:int):
        """
        :param need_translate: 表示本动态是否需要翻译的整数, 只取0和1
        """
        message = f'{self.author_name}转发了一条动态:\n'\
                + (f'--------------------\n{self.text}\n' if self.text else '')\
                + (f'--------------------\n机翻:\n{self.translate_text}\n' * need_translate)\
                + f'--------------------\n引用自{self.orig_author_name}:\n'
        # 转发视频
        if self.orig_type == DynamicType.VIDEODYNAMIC:
            message += f'{self.orig_text}\n'\
                     + f'--------------------\n视频标题:「{self.orig_video_title}」\n'
        # 转发专栏
        elif self.orig_type == DynamicType.COLUMNDYNAMIC:
            message += f'--------------------\n专栏标题:「{self.orig_column_title}」\n'\
                     + f'简介: {self.orig_column_summary}...\n'
        # 转发图片或文字
        else:
            message += f'{self.orig_text}\n'
        message += f'--------------------\n{self.url}\n'
        message += f'(id: {self.dynamic_id})\n'
        message = Message(message)
        for img in self.orig_image_urls:
            message.append(MessageSegment.image(img))
        return message

class ImageDynamic(Dynamic):
    """
    带图动态ImageDynamic类, 从返回的response中提取动态相关的信息\n
    回复使用'rid'
    """
    def __init__(self, dy_info:dict, credential:Credential):
        """
        :param dy_info: API返回的动态信息字典
        """
        Dynamic.__init__(self, dy_info, credential)
        self.url = f'https://t.bilibili.com/{self.dynamic_id}'
        self.reply_id = dy_info['desc']['rid']
        self.text = dy_info['card']['item']['description']

    def make_message(self, need_translate:int):
        """
        :param need_translate: 表示本动态是否需要翻译的整数, 只取0和1
        """
        message = f'{self.author_name}发布了一条新动态:\n'\
                + (f'--------------------\n{self.text}\n' if self.text else '')\
                + (f'--------------------\n机翻:\n{self.translate_text}\n' * need_translate)\
                + f'--------------------\n{self.url}\n'\
                + f'(id: {self.dynamic_id})\n'
        message = Message(message)
        for img in self.image_urls:
            message.append(MessageSegment(img))
        return message

class TextDynamic(Dynamic):
    """
    文本动态TextDynamic类, 从返回的response中提取动态相关的信息\n
    回复使用'dynamic_id'
    """
    def __init__(self, dy_info:dict, credential:Credential):
        Dynamic.__init__(self, dy_info, credential)
        self.url = f'https://t.bilibili.com/{self.dynamic_id}'
        self.reply_id = dy_info['desc']['dynamic_id']
        self.text = dy_info['card']['item']['content']

    def make_message(self, need_translate:int) -> Message:
        """
        :param need_translate: 表示本动态是否需要翻译的整数, 只取0和1
        """
        message = f'{self.author_name}发布了一条新动态:\n'\
                + f'--------------------\n{self.text}\n'\
                + (f'--------------------\n机翻:\n{self.translate_text}\n' * need_translate)\
                + f'--------------------\n{self.url}\n'\
                + f'(id: {self.dynamic_id})\n'
        message = Message(message)
        return message
        
class VideoDynamic(Dynamic):
    """
    视频动态VideoDynamic类, 从返回的response中提取动态相关的信息\n
    伴随着视频发布可能会有文字的动态信息\n
    回复使用'rid'
    """
    def __init__(self, dy_info:dict, credential:Credential):
        # 动态基本信息
        Dynamic.__init__(self, dy_info, credential)
        self.reply_id = dy_info['desc']['rid']
        self.text = ""
        if 'dynamic' in dy_info['card']:
            self.text = dy_info['card']['dynamic']
        # 视频信息
        self.bvid = dy_info['desc']['bvid']
        self.video_title = dy_info['card']['title']
        self.video_desc = dy_info['card']['desc']
        self.video_pic_url = dy_info['card']['pic']
        self.video_duration = dy_info['card']['duration']
        self.url = f'https://www.bilibili.com/video/{self.bvid}'
    
    def make_message(self, need_translate:int):
        """
        :param need_translate: 表示本动态是否需要翻译的整数, 只取0和1
        """
        message = f'{self.author_name}发布了一个新视频:\n'\
                + (f'--------------------\n{self.text}\n' if self.text else "")\
                + (f'--------------------\n机翻:\n{self.translate_text}\n' * need_translate)\
                + '--------------------\n'\
                + f'标题: 「{self.video_title}」\n'\
                + f'简介: {self.video_desc}\n'\
                + f'--------------------\n{self.url}\n'\
                + f'(id: {self.dynamic_id})\n'
        message = Message(message)
        message.append(MessageSegment.image(self.video_pic_url))
        return message
    
CLASS_MAP = {
    DynamicType.REPOST : Repost,
    DynamicType.IMAGEDYNAMIC : ImageDynamic,
    DynamicType.TEXTDYNAMIC : TextDynamic,
    DynamicType.VIDEODYNAMIC : VideoDynamic
}

async def get_users_timeline(credential:Credential, *uids:int) -> list[dict]:
    """
    获取复数用户的最新动态，
    :return 每个用户最新动态的字典列表, 顺序与输入顺序一致
    """
    tasks = []
    for uid in uids:
        task = asyncio.create_task(get_ones_timeline(uid, credential))
        tasks.append(task)
    try:
        data = await asyncio.gather(*tasks)
    except:
        data = []
        logger.error('获取动态失败, 请检查网络链接或用户uid')
    return data

async def get_ones_timeline(uid:int, credential:Credential) -> dict:
    """
    获取给定用户的最新动态, 一般数量为最新12条
    """
    u = user.User(uid, credential)
    page = await u.get_dynamics()
    if 'cards' in page:
        dynamics = page['cards']
    return dynamics