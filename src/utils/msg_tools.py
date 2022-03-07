# -*- coding: utf-8 -*-
import emoji
import re
from typing import Tuple
from nonebot.adapters.onebot.v11 import Message


EMOJI_REX = emoji.get_emoji_regexp()
EMOJI_DELIMITER = "@em@"
EMOJI_DELIMITER_REX = re.compile(EMOJI_DELIMITER)
TEXT_DELIMITERS = {
    'face':'@fc@', 'image':'@im@', 'record':'@rc@', 'video':'@vd@', 'at':'@at@',
    'rps':'@rp@', 'dice':'@dc@', 'shake':'@sk@', 'poke':'@pk@',
    'anonymous':'@an@', 'share':'@sr@', 'contact':'@cn@', 'location':'@lc@',
    'music':'@ms@', 'reply':'@rl@', 'forward':'@fw@', 'node':'@nd@', 
    'xml':'@xm@', 'json':'@js@'
}
TEXT_DELIMITERS_REX = re.compile(
    '(@' + '@|@'.join(value[1:3] for key, value in TEXT_DELIMITERS.items()) + '@)',
    )
PLAIN_TEXT = ['text', 'face', 'reply', 'at']


def extract_emoji(string:str) -> Tuple[str,list[str]]:
    """
    extract emoji from a given string text.
    all emoji in text will be replaced by a pre-defined delimiter
    """
    words = EMOJI_REX.split(string)
    emoji_list = EMOJI_REX.findall(string)
    new_string = EMOJI_DELIMITER.join(word for word in words if word not in emoji_list)
    return new_string, emoji_list

def recover_emoji(string:str, emojis:list[str]) -> str:
    """
    recover a string text from a plain text and list of emoji
    given palin text must be generate by extract_emoji(),
    or delimited by a pre-defined delimiter
    """
    words = EMOJI_DELIMITER_REX.split(string)
    new_string = ""
    for i in range(len(emojis)):
        new_string += words[i] + emojis[i]
    new_string += words[-1]
    return new_string

def extract_nontext(message:Message) -> str:
    """
    extract all non-text content from a given Message object.
    notice that emoji will not extracted by this function
    """
    new_text = ""
    for seg in message:
        if seg['type'] == 'text':
            new_text += seg.data["text"]
        else:
            new_text += TEXT_DELIMITERS[seg['type']]
    return new_text

def replace_whole_text(message:Message, plain_text:str) -> Message:
    new_message = message[:]
    words = TEXT_DELIMITERS_REX.split(plain_text)
    for i in range(len(new_message)):
        if new_message[i]['type'] == 'text':
            new_message[i]['text'] = words[i]
    return new_message

def replace_plain_text(message:Message, plain_text:str) -> Message:
    new_message = message[:]
    words = TEXT_DELIMITERS_REX.split(plain_text)
    i = 0
    while i != len(new_message):
        if new_message[i]['type'] == 'text':
            new_message[i]['text'] = words[i]
        elif new_message[i]['type'] not in PLAIN_TEXT:
            del new_message[i]
            i -= 1
        i += 1
    return new_message

