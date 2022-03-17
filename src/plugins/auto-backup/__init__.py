from importlib.resources import path
import nonebot
from nonebot import require
import time
import os

# 读取备份地址
BACKUP_PATH = SESSDATA = nonebot.get_driver().config.dict()['backup_path']
# 创建用于保存备份数据库的文件夹
try:
    os.mkdir(BACKUP_PATH)
except FileExistsError:
    pass

auto_backup = require('nonebot_plugin_apscheduler').scheduler
# 每周UTC Sun. 20:00(GTM+8, Mon. 4:00)启动自动备份, 
@auto_backup.scheduled_job('cron', 
    day_of_week='thu', hour=5, minute=20, 
    timezone='UTC', id='db_backup')

async def backup():
    for job in auto_backup.get_jobs():
        job.pause()
    date = time.strftime('%Y%m%d',time.gmtime(time.time() + 8 * 60 * 60))  # 文件名时间用GTM+8
    try:
        os.mkdir(f'{BACKUP_PATH}/botDB_backup_{date}')
    except FileExistsError:
        pass
    os.system(f'cp -r data {BACKUP_PATH}/botDB_backup_{date}')
    for job in auto_backup.get_jobs():
        job.resume()