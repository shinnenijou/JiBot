# -*- coding: utf-8 -*-
import emoji
from typing import Tuple
from nonebot.adapters.onebot.v11 import Message, MessageSegment

# CONSTANT
PLAIN_TEXT = ['face', 'reply', 'at', 'text']
class MessageFragments():

    def __init__(self, message : Message) -> None:
        # list[[list[text], list[emoji]]]
        self.fragments =[None] * len(message)
        self.plain_text = []
        self.message = Message()
        if message:
            self.message = message
            i = 0
            while i < len(message):
                if message[i].type == 'text':
                    text_list, emoji_list = split_emoji(message[i].data['text'])
                    self.fragments[i] = [text_list, emoji_list]
                    for text in self.fragments[i][0]:
                        self.plain_text.append(text)
                elif message[i].type not in PLAIN_TEXT:
                    del message[i]
                    i -= 1
                i += 1
    
    def copy(self):
        return MessageFragments([])._copy_from(self.message, self.plain_text, self.fragments)

    def update_plain_text(self, text_list : list[str]) -> None:
        count = 0
        self.plain_text = text_list
        for i in range(len(self.fragments)):
            if isinstance(self.fragments[i], list):
                for j in range(len(self.fragments[i][0])):
                    self.fragments[i][0][j] = text_list[count]
                    count += 1
                self.message[i] = MessageSegment.text(
                    merge_emoji(
                        self.fragments[i][0],
                        self.fragments[i][1]
                    )
                )

    def get_message(self) -> Message:
        return self.message

    def get_plain_text(self) -> list[str]:
        return self.plain_text

    def _copy_from(self, message: Message, plain_text : list[str],
        fragments:list):
        self.fragments = fragments.copy()
        self.message = message.copy()
        self.plain_text = plain_text.copy()
        return self

def _extract(string: str, emoji_list: list[dict[str,str]],
    string_only : list[str], emoji_only : list[str]) -> None:
    if len(emoji_list):
        parts = string.partition(emoji_list[0]['emoji'])
        string_only.append(parts[0])
        emoji_only.append(parts[1])
        _extract(parts[2], emoji_list[1:], string_only, emoji_only)
    else:
        string_only.append(string)
    return string_only, emoji_only

def split_emoji(string : str) -> Tuple[list[str], list[str]]:
    string_only, emoji_only = [], []
    emoji_list = emoji.emoji_lis(string)
    return _extract(string, emoji_list, string_only, emoji_only)

def merge_emoji(text_only : list[str], emoji_only : list[str]) -> str:
    i = 0
    string = ""
    while i < len(text_only) and i < len(emoji_only):
        string += text_only[i] + emoji_only[i]
        i += 1
    while i < len(text_only):
        string += text_only[i]
        i += 1
    while i < len(emoji_only):
        string += emoji_only[i]
        i += 1
    return string