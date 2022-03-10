# -*- coding: utf-8 -*-
import nonebot
import src.plugins.manual_translator.tmt as tmt
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, Message, MessageSegment
from nonebot import on_command

# HELP
helper = nonebot.on_command(
    cmd="翻译帮助", temp=False, priority=5, block=True,
    permission=GROUP
)
@helper.handle()
async def help():
    menu = '翻译模块目前支持的功能:\n\n'
    menu += '命令格式: "/翻译 待翻译文本"'
    await helper.finish(menu)

# TRANSLATE
manual_translator = on_command(cmd="翻译", temp=False,
    priority=5, block=True, permission=GROUP)
@manual_translator.handle()
async def translate(event: GroupMessageEvent):
    cmd = event.get_plaintext().split()
    message_id = event.get_event_description().split()[1]
    text_start = 2
    if len(cmd) > 1:
        target = cmd[1]
        if len(target) != 2 or not target.isascii():
            target = 'ja'
            text_start = 1
        source_text = "".join(cmd[i] for i in range(text_start, len(cmd)))
        target_text = "机翻：\r\n" + (await tmt.translate('auto', target, 
            source_text.replace("http://", "").replace("https://", "")))[0]
        msg = Message(target_text)
        msg.insert(0, MessageSegment(type='reply', data={'id':message_id}))
        await manual_translator.send(msg)