from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile

import nonebot
from nonebot.matcher import Matcher
from nonebot import on_message, on_command
from nonebot.permission import SUPERUSER, USER
from nonebot.adapters.onebot.v11 import GroupMessageEvent

import json

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
    with open("./jibot/plugins/user_translator/config.ini", "r") as file:
        TRANSLATE_USERS = json.loads(file.read())
except FileNotFoundError:
    TRANSLATE_USERS = {}
    with open("./jibot/plugins/user_translator/config.ini", "w") as file:
        file.write(json.dumps(TRANSLATE_USERS))

# DEBUG
admin = on_command(cmd="翻译状态",temp=False, priority=1, block=True,
    permission=SUPERUSER)
@admin.handle()
async def del_user(event:GroupMessageEvent):
    group_id = event.get_session_id().partition('_')[1]
    msg = "以下成员的发言翻译功能正在运行: "
    for key, value in TRANSLATE_USERS.items():
        if group_id in key:
            msg += f"\r\nQQ{key.rpartition('_')[2]}: {value['source']}->{value['target']}"
    await admin.send(msg)

# EVENT: add translate user
admin = on_command(cmd="开启翻译",temp=False, priority=1, block=True,
    permission=SUPERUSER)
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
        with open("./jibot/plugins/user_translator/config.ini", "r") as file:
            config = json.loads(file.read())
        if session_id not in config:
            config[session_id] = {"source":source, "target":target}
            file = open("./jibot/plugins/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            file.close()
            await admin.send(f"成功开启 QQ{user_id} 的发言翻译功能")
            TRANSLATE_USERS = config
            translator.permission = USER(*TRANSLATE_USERS.keys())
        else:
            await admin.send(f"QQ{user_id} 的发言翻译功能正在运行")

# EVENT: delete translate user
admin = on_command(cmd="关闭翻译",temp=False, priority=1, block=True,
    permission=SUPERUSER)
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
        with open("./jibot/plugins/user_translator/config.ini", "r") as file:
            config = json.loads(file.read())
        if session_id in config:
            del config[session_id]
            file = open("./jibot/plugins/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            await admin.send(f"成功关闭 QQ{user_id} 的发言翻译功能")
            file.close()
            TRANSLATE_USERS = config
            translator.permission = USER(*TRANSLATE_USERS.keys())
        else:
            await admin.send(f"QQ{user_id} 的发言翻译功能未开启")

# Event: translate for particular users
translator = on_message(temp=False, priority=2, block=True,
    permission=USER(*TRANSLATE_USERS.keys()))

@translator.permission_updater
async def update(matcher:Matcher):
    return matcher.permission

@translator.handle()
async def translate(event:GroupMessageEvent):
    req.SourceText = event.get_plaintext()
    req.Source = TRANSLATE_USERS[event.get_session_id()]["source"]
    req.Target = TRANSLATE_USERS[event.get_session_id()]["target"]
    try:
        resp = client.TextTranslate(req)
        msg = "【自動翻訳】" + json.loads(resp.to_json_string())['TargetText']
        await admin.send(msg)
    except TencentCloudSDKException as err:
        await nonebot.get_bot().send_group_msg(
            group_id=nonebot.get_driver().config.dict()["admin_group"],
            message=str(err)
        )