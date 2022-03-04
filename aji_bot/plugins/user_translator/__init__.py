import nonebot
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile
from nonebot import on_message, on_command
from nonebot.permission import SUPERUSER, USER
from nonebot.adapters.onebot.v11 import GroupMessageEvent
import json

# set Tencent TMT API
SECRETID = str(nonebot.get_driver().config.dict()["api_secretid"])
SECRETKEY = str(nonebot.get_driver().config.dict()["api_secretkey"])
cred = credential.Credential(SECRETID, SECRETKEY)
httpProfile = HttpProfile(endpoint="tmt.ap-tokyo.tencentcloudapi.com")
clientProfile = ClientProfile(
    signMethod="TC3-HMAC-SHA256",
    language="en-US",
    httpProfile=httpProfile
)
client = tmt_client.TmtClient(cred, "ap-seoul", clientProfile)
req = models.TextTranslateRequest()
req.Source = "ja"
req.Target = "zh"
req.ProjectId = 0

# load translate users config
try:
    with open("./aji_bot/plugins/user_translator/config.ini", "r") as file:
        TRANSLATE_USERS = tuple(json.loads(file.read()))
except FileNotFoundError:
    TRANSLATE_USERS = ()

# EVENT: add translate user
matcher = on_command(cmd="开启翻译",temp=False, priority=1, block=True,
    permission=SUPERUSER)
@matcher.handle()
async def add_user(event:GroupMessageEvent):
    global TRANSLATE_USERS
    cmd = event.get_plaintext().split()[1]
    if cmd.isdigit():
        session_id = f"{event.get_session_id().rpartition('_')[0]}_{cmd}"
        try:
            file = open("./aji_bot/plugins/user_translator/config.ini", "r")
            config = json.loads(file.read())
        except:
            file = open("./aji_bot/plugins/user_translator/config.ini", "w")
            config = []
            file.write(json.dumps(config))
        file.close()
        if session_id not in config:
            config.append(session_id)
            file = open("./aji_bot/plugins/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            file.close()
            await matcher.send(f"成功开启 QQ{cmd} 的发言翻译功能")
            TRANSLATE_USERS = tuple(config)
        else:
            await matcher.send(f"QQ{cmd} 的发言翻译功能正在运行")

# EVENT: delete translate user
matcher = on_command(cmd="关闭翻译",temp=False, priority=1, block=True,
    permission=SUPERUSER)
@matcher.handle()
async def del_user(event:GroupMessageEvent):
    global TRANSLATE_USERS
    cmd = event.get_plaintext().split()[1]
    if cmd.isdigit():
        session_id = f"{event.get_session_id().rpartition('_')[0]}_{cmd}"
        try:
            file = open("./aji_bot/plugins/user_translator/config.ini", "r")
            config = json.loads(file.read())
        except:
            file = open("./aji_bot/plugins/user_translator/config.ini", "w")
            config = []
            file.write(json.dumps(config))
        file.close()
        if session_id in config:
            config.remove(session_id)
            file = open("./aji_bot/plugins/user_translator/config.ini", "w")
            file.write(json.dumps(config))
            await matcher.send(f"成功关闭 QQ{cmd} 的发言翻译功能")
            file.close()
            TRANSLATE_USERS = tuple(config)
        else:
            await matcher.send(f"QQ{cmd} 的发言翻译功能未开启")

# Event: translate for particular users
matcher = on_message(temp=False, priority=2, block=True,
    permission=USER(*TRANSLATE_USERS))
@matcher.handle()
async def translate(event:GroupMessageEvent):
    req.SourceText = event.get_plaintext()
    try:
        resp = client.TextTranslate(req)
        msg = json.loads(resp.to_json_string())['TargetText']
        await matcher.send(msg)
    except TencentCloudSDKException as err:
        await nonebot.get_bot().send_group_msg(
            group_id=nonebot.get_driver().config.dict()["admin_group"],
            message=str(err)
        )