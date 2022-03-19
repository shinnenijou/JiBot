import nonebot
from bilibili_api import user, Credential

# Credential
SESSDATA = nonebot.get_driver().config.dict()['bili_sessdata']
BILI_JCT = nonebot.get_driver().config.dict()['bili_jct']
BUVID3 = nonebot.get_driver().config.dict()['bili_buvid3']
CREDENTIAL = Credential(SESSDATA, BILI_JCT, BUVID3)
# Constant
DYNAMIC_LISTEN_INTERVAL = nonebot.get_driver().config.dict()['dynamic_listen_interval']
ADMIN_GROUP = int(nonebot.get_driver().config.dict()['admin_group'])

scheduler = nonebot.require('nonebot_plugin_apscheduler').scheduler
@scheduler.scheduled_job('interval', seconds=DYNAMIC_LISTEN_INTERVAL, id='miriya_pusher')
async def listen_miriya():
    u = user.User(1838190318, CREDENTIAL)
    info = await u.get_user_info()
    if not info['live_room'] is None:
        await nonebot.get_bot().send_group_msg(
            group_id=ADMIN_GROUP,
            message='魔狼咪莉娅直播间状态更新啦！！！'
        )