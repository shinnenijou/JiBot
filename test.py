import psutil
import os
import random
from datetime import datetime
import pytz
import time


def rand_datetime(offset: int = 0, timezone:str = "Asia/Shanghai") -> str:
    timestamp = time.time() - offset - random.randint(1, 7 * 24 * 60 * 60)
    
    tz = pytz.timezone(timezone)
    dt_now = datetime.fromtimestamp(timestamp, tz)
    return dt_now.strftime("%Y%m%d_%H%M%S")

def now_datetime(timezone:str = "Asia/Shanghai"):
    tz = pytz.timezone(timezone)
    dt_now = datetime.now(tz)
    return dt_now.strftime("%Y%m%d_%H%M%S")

# generate test file
target_path = os.path.join('.', 'data', 'recorder', 'record')

path_a = os.path.join(target_path, 'test_a')
if not os.path.exists(path_a):
    os.mkdir(path_a)

path_b = os.path.join(target_path, 'test_b')
if not os.path.exists(path_b):
    os.mkdir(path_b)

path_c = os.path.join(target_path, 'test_c')
if not os.path.exists(path_c):
    os.mkdir(path_c)

dir_list = os.listdir(target_path)

for _ in range(100):
    if psutil.disk_usage("/").free < 10 * 1024 * 1024 * 1024:
        break

    for dir in dir_list:
        if psutil.disk_usage("/").free < 10 * 1024 * 1024 * 1024:
            break

        timestr = rand_datetime(24 * 60 * 60)
        filename = f"{timestr}_title_{dir}.mp4"
    
        cmds = ['dd', 'if=/dev/zero', f'of={os.path.join(target_path, dir, filename)}', 'bs=1G', 'count=1']
        os.system(' '.join(cmd for cmd in cmds))

for _ in range(100):
    if psutil.disk_usage("/").free < 2 * 1024 * 1024 * 1024:
        break 

    for dir in dir_list:
        if psutil.disk_usage("/").free < 2 * 1024 * 1024 * 1024:
            break

        timestr = now_datetime()
        filename = f"{timestr}_title_{dir}.mp4"
                
        cmds = ['dd', 'if=/dev/zero', f'of={os.path.join(target_path, dir, filename)}', 'bs=1G', 'count=1']
        os.system(' '.join(cmd for cmd in cmds))