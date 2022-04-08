# -*- coding: utf-8 -*-
from os import mkdir
import nonebot
import bilibili_api
from nonebot import require, on_command
from bilibili_api import Credential, video
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GroupMessageEvent

# init
try:
    mkdir('./data/video_stat')
except FileExistsError:
    pass
# Credential
SESSDATA = nonebot.get_driver().config.dict()['bili_sessdata']
BILI_JCT = nonebot.get_driver().config.dict()['bili_jct']
BUVID3 = nonebot.get_driver().config.dict()['bili_buvid3']
CREDENTIAL = Credential(SESSDATA, BILI_JCT, BUVID3)

# CONSTANT 
VIDEO_STAT_INTERVAL = 600
STAT_MAXLIMIT = 1000
VIDEOS = {}
# GLOBAL VARIABLES

# 请求定时任务对象scheduler
scheduler = require('nonebot_plugin_apscheduler').scheduler

@scheduler.scheduled_job('interval', seconds=VIDEO_STAT_INTERVAL,
    id='video_stat')
async def stat():
    expired_video = []
    for bvid in VIDEOS.keys():
        VIDEOS[bvid] -= 1
        if VIDEOS[bvid] == 0:
            expired_video.append(bvid)
        v = video.Video(bvid=bvid, credential=CREDENTIAL)
        info = await v.get_info()
        no = STAT_MAXLIMIT - VIDEOS[bvid]
        view = info['stat']['view']
        favorite = info['stat']['favorite']
        coin = info['stat']['coin']
        like = info['stat']['like']
        print(f'{no},{view},{favorite},{coin},{like}')
        with open(f'./data/video_stat/{bvid}.csv', 'a') as file:
            file.write(f'{no},{view},{favorite},{coin},{like}\n')
    for bvid in expired_video:
        del VIDEOS[bvid]
        
# 添加统计播放的视频
add_video = on_command(cmd='统计视频', temp=False, priority=2, block=True,
    permission=SUPERUSER)
@add_video.handle()
async def _(event: GroupMessageEvent):
    global VIDEOS
    cmd = event.get_plaintext().split()
    if len(cmd) == 2:
        VIDEOS[cmd[1]] = STAT_MAXLIMIT # 统计1000次数据
        with open(f'./data/video_stat/{cmd[1]}.csv', 'a') as file:
            file.write('No,view,favorite,coin,like\n')
        await add_video.send('视频数据统计添加成功, 将统计1000次数据')