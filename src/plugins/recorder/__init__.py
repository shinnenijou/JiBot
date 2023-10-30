import os
import json
from threading import Event

from nonebot import require

from src.plugins.recorder.listen import listen, get_driver
from src.plugins.recorder.record import Recorder
from src.plugins.recorder.threads import thread_pool

from src.common.utils import get_datetime

# A map Store the record status flag. streamer -> Event
record_status: dict[str, Event] = {}

# Constant
RECORD_FORMAT = 'ts'

# Initialize
DATA_DIR = os.path.join(get_driver().config.dict()['data_path'], 'recorder')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
RECORD_DIR = os.path.join(DATA_DIR, 'record')
RECORD_LISTEN_INTERVAL = int(get_driver().config.dict()['record_listen_interval'])
TEMP_DIR = os.path.join(get_driver().config.dict()['data_path'], 'recorder', 'temp')

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

if not os.path.exists(RECORD_DIR):
    os.mkdir(RECORD_DIR)

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as file:
        file.write("{}")

if not os.path.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)

# Add schedule task
scheduler = require('nonebot_plugin_apscheduler').scheduler


@scheduler.scheduled_job('interval', seconds=RECORD_LISTEN_INTERVAL, id='recorder', timezone='Asia/Shanghai')
def try_record():
    try:
        with open(CONFIG_FILE, 'r') as file:
            config: dict = json.loads(file.read())
    except:
        return

    if 'record_list' not in config:
        return

    # clean zombie thread
    thread_pool.clean_threads()

    for streamer_name, record_config in config['record_list'].items():
        if not record_config.get('record', False):
            continue

        if streamer_name in record_status and record_status[streamer_name].is_set():
            continue

        if 'platform' not in record_config:
            continue

        if 'id' not in record_config:
            continue

        if 'url' not in record_config:
            continue

        live_status: dict = listen(record_config['platform'], record_config['id'])

        if not live_status.get('Result', False):
            continue

        if not os.path.exists(os.path.join(RECORD_DIR, streamer_name)):
            os.mkdir(os.path.join(RECORD_DIR, streamer_name))

        # record args
        filename = f"{get_datetime('Asia/Shanghai')}_{live_status.get('Title', '')}_{streamer_name}"
        out_path = os.path.join(RECORD_DIR, streamer_name, f"{filename}.{RECORD_FORMAT}")

        # 需要保证不会重复录像, 但录像完成后还需要转码的时间，这段时间是可以进行新的录像任务的
        # 不能按照线程的生命周期去判断, 需要使用额外的Event, 在进程内自行进行状态的记录
        record_status[streamer_name] = Event()
        recorder = Recorder(
            streamer=streamer_name,
            live_url=record_config['url'],
            out_path=out_path,
            running_flag=record_status[streamer_name],
            notice_group=record_config.get('notice_group', ''),
            upload_to=f"{record_config.get('upload_to', '')}/{streamer_name}",
            options=record_config.get('options', {}),
            name=filename,
        )

        # 先启动后加入线程池
        recorder.start()
        thread_pool.add_thread(recorder)
