from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile

import nonebot
from nonebot.matcher import Matcher
from nonebot import on_message, on_command
from nonebot.permission import USER, SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

import emoji

import json
from os import mkdir
# tools function/class
class EmojiStr:
    def __init__(self, string:str, plist: list = []) -> None:
        self.string = string
        self.emojis = plist

def extract_emoji(estr:EmojiStr):
    # beg indicates valid chars' begin
    beg = 0
    new_estr = EmojiStr("", estr.emojis[:])
    emojis = emoji.emoji_lis(estr.string)
    for e in emojis:
        new_estr.string += estr.string[beg: e['location']] + f"[{len(new_estr.emojis)}]"
        new_estr.emojis.append(e['emoji'])
        beg = e['location'] + 1
    new_estr.string += estr.string[beg:]
    return new_estr

def recover_str(estr:EmojiStr):
    # end indicates valid chars' end, and beg indicates valid chars' begin
    beg, end = 0, 0
    new_estr = EmojiStr("")
    while end != -1 and beg < len(estr.string) - 1:
        end = estr.string.find('[', beg)
        if end != -1:
            new_estr.string += estr.string[beg : end]
            beg = estr.string.find(']', end)
            if beg != -1:
                new_estr.string += estr.emojis[int(estr.string[end + 1:beg])]
                beg += 1
            else:
                break
    new_estr.string += estr.string[beg:]
    return new_estr.string

# set Tencent TMT API
SECRETID = str(nonebot.get_driver().config.dict()["api_secretid"])
SECRETKEY = str(nonebot.get_driver().config.dict()["api_secretkey"])
REGION = str(nonebot.get_driver().config.dict()["api_region"])
cred = credential.Credential(SECRETID, SECRETKEY)
httpProfile = HttpProfile(endpoint="tmt.ap-tokyo.tencentcloudapi.com")
clientProfile = ClientProfile(
    signMethod="TC3-HMAC-SHA256",
    language="en-US",
    httpProfile=httpProfile
)
client = tmt_client.TmtClient(cred, REGION, clientProfile)
req = models.TextTranslateRequest()
req.ProjectId = 0

# load translate users config
try:
    mkdir("./data/user_translator")
except FileExistsError:
    pass
try:    
    with open("./data/user_translator/config.ini", "r") as file:
        TRANSLATE_USERS = json.loads(file.read())
except FileNotFoundError:
    TRANSLATE_USERS = {}
    with open("./data/user_translator/config.ini", "w") as file:
        file.write(json.dumps(TRANSLATE_USERS))

# DEBUG
admin = on_command(cmd="翻译列表",temp=False, priority=1, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def del_user(event:GroupMessageEvent):
    group_id = event.get_session_id().partition('_')[1]
    msg = "以下成员的发言翻译功能正在运行: "
    for key, value in TRANSLATE_USERS.items():
        if group_id in key:
            msg += f"\r\nQQ{key.rpartition('_')[2]}: {value['source']}->{value['target']}"
    await admin.send(msg)

# EVENT: add translate user
admin = on_command(cmd="翻译关注",temp=False, priority=1, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def add_user(event:GroupMessageEvent):
    global TRANSLATE_USERS
    try:
        user_id = event.get_plaintext().split()[1]
        setting = event.get_plaintext().split()[2]
        source = setting.partition("->")[0]
        target = setting.partition("->")[2]
        isValidCmd = user_id.isdigit() and source and target
    except:
        isValidCmd = False
    if isValidCmd:
        session_id = f"{event.get_session_id().rpartition('_')[0]}_{user_id}"
        with open("./data/user_translator/config.ini", "r") as file:
            config = json.loads(file.read())
        if session_id not in config:
            config[session_id] = {"source":source, "target":target}
            file = open("./data/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            file.close()
            await admin.send(f"成功开启 QQ{user_id} 的发言翻译功能")
            TRANSLATE_USERS = config
            translator.permission = USER(*TRANSLATE_USERS.keys())
        else:
            await admin.send(f"QQ{user_id} 的发言翻译功能正在运行")

# EVENT: delete translate user
admin = on_command(cmd="翻译取关",temp=False, priority=1, block=True,
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND | SUPERUSER)
@admin.handle()
async def del_user(event:GroupMessageEvent):
    global TRANSLATE_USERS
    try:
        user_id = event.get_plaintext().split()[1]
        isValidCmd = user_id.isdigit()
    except:
        isValidCmd = False
    if isValidCmd:
        session_id = f"{event.get_session_id().rpartition('_')[0]}_{user_id}"
        with open("./data/user_translator/config.ini", "r") as file:
            config = json.loads(file.read())
        if session_id in config:
            del config[session_id]
            file = open("./data/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            await admin.send(f"成功关闭 QQ{user_id} 的发言翻译功能")
            file.close()
            TRANSLATE_USERS = config
            translator.permission = USER(*TRANSLATE_USERS.keys())
        else:
            await admin.send(f"QQ{user_id} 的发言翻译功能未开启")

# Event: translate for particular users
translator = on_message(temp=False, priority=5, block=True,
    permission=USER(*TRANSLATE_USERS.keys()))

@translator.permission_updater
async def update(matcher:Matcher):
    return matcher.permission

@translator.handle()
async def translate(event:GroupMessageEvent):
    msg = event.get_message()
    source_text = ""
    for seg in msg:
        if "text" in seg.data:
            source_text += seg.data["text"]
        else:
            source_text += "|@-@|"
    print(source_text)
    if source_text != "|@-@|":
        extractedMsg =  extract_emoji(EmojiStr(source_text))
        req.SourceText =extractedMsg.string
        req.Source = TRANSLATE_USERS[event.get_session_id()]["source"]
        req.Target = TRANSLATE_USERS[event.get_session_id()]["target"]
        try:
            resp = client.TextTranslate(req)
            extractedMsg.string = json.loads(resp.to_json_string())['TargetText']
            target_texts = recover_str(extractedMsg).split('|@-@|')
            i, j = 0, 0
            while i != len(msg):
                if "text" in msg[i].data:
                    msg[i].data["text"] = target_texts[j]
                    j += 1
                elif "id" not in msg[i].data:
                    msg.remove(msg[i])
                    i -= 1
                i += 1
            msg.insert(0, MessageSegment(type='text', data={'text': '【机翻】'}))
            await translator.send(msg)
        except Exception as err:
            await nonebot.get_bot().send_group_msg(
                group_id=nonebot.get_driver().config.dict()["admin_group"],
                message=event.get_plaintext() + "\r\nError: " + str(err)
            )