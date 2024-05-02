import os
import json
import signal
from multiprocessing import Queue
from threading import Thread

from nonebot import require, get_driver, logger

from src.plugins.recorder.listen import listener
from src.plugins.recorder.record import Recorder, upload, send_to_bark
from src.plugins.recorder.threads import task_manager
from src.plugins.recorder.clean import cleaner
from src.plugins.recorder.http_server import HttpServerProcess

from src.common.utils import get_datetime, send_to_admin

# Initialize
DATA_DIR = os.path.join(get_driver().config.dict()['data_path'], 'recorder')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
RECORD_DIR = os.path.join(DATA_DIR, 'record')
RECORD_LISTEN_INTERVAL = int(get_driver().config.dict()[
                             'record_listen_interval'])
TEMP_DIR = os.path.join(get_driver().config.dict()[
                        'data_path'], 'recorder', 'temp')
STREAMERS = {}

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

queue = Queue()

@scheduler.scheduled_job('interval', seconds=RECORD_LISTEN_INTERVAL, id='recorder', timezone='Asia/Shanghai')
async def try_record():
    try:
        with open(CONFIG_FILE, 'r', encoding="utf-8") as file:
            config: dict = json.loads(file.read())
    except:
        return

    if 'record_list' not in config:
        return

    # clean zombie thread
    task_manager.clean_threads()

    # clean disk
    cleaner.clean(RECORD_DIR)

    # Upload bililive recorder's files
    while not queue.empty():
        data = queue.get()
        relative_path = data.get('EventData', {}).get('RelativePath', '')

        if not relative_path:
            continue

        streamer = relative_path.partition('/')[0]
        filename = relative_path.partition('/')[2]
        path = os.path.join(RECORD_DIR, streamer, filename)

        if not os.path.exists(path):
            continue

        if streamer not in config['record_list']:
            continue

        if 'upload_to' not in config['record_list'][streamer]:
            continue

        logger.info(config['record_list'][streamer]['upload_to'])

        os.rename(os.path.abspath(path), os.path.abspath(os.path.join(RECORD_DIR, streamer, filename.replace(" ", "_"))))
        path = os.path.join(RECORD_DIR, streamer, filename.replace(" ", "_"))

        thread = Thread(target=upload, args=(f"{config['record_list'][streamer]['upload_to']}/{streamer}", path))
        thread.start()
        task_manager.add_thread(thread)

    for streamer_name, record_config in config['record_list'].items():
        if not record_config.get('record', False):
            continue

        if task_manager.is_recording(streamer_name):
            continue

        if 'platform' not in record_config:
            continue

        if 'id' not in record_config:
            continue

        if 'url' not in record_config:
            continue

        # 监听对象记录一下日志
        if streamer_name not in STREAMERS:
            logger.info(f"添加录像监听对象: {streamer_name}")
            STREAMERS[streamer_name] = True

        live_status: dict = await listener.listen(record_config['platform'], record_config['id'])

        if not live_status.get('Result', False):
            continue

        if not os.path.exists(os.path.join(RECORD_DIR, streamer_name)):
            os.mkdir(os.path.join(RECORD_DIR, streamer_name))

        # 开始录像前检查磁盘空间, 空间不足时向管理员发出警告
        if not cleaner.disk_enough():
            await send_to_admin("[Warning][Recorder]Disk NOT ENOUGH.")

        # record file (WITHOUT extension filename)
        filename = f"{get_datetime('Asia/Shanghai')}_{live_status.get('Title', '')}_{streamer_name}"
        out_path = os.path.join(RECORD_DIR, streamer_name, f"{filename}")

        # 需要保证不会重复录像, 但录像完成后还需要转码的时间，这段时间是可以进行新的录像任务的
        # 不能按照线程的生命周期去判断, 需要使用额外的Event, 在进程内自行进行状态的记录
        recorder = Recorder(
            streamer=streamer_name,
            live_url=record_config['url'],
            out_path=out_path,
            running_flag=task_manager.add_recording(streamer_name),
            notice_group=record_config.get('notice_group', ''),
            upload_to=f"{record_config.get('upload_to', '')}/{streamer_name}",
            options=record_config.get('options', {}),
            name=filename,
        )

        # 先启动后加入线程池
        recorder.start()
        task_manager.add_thread(recorder)


http_server = None


@get_driver().on_startup
def startup():
    global http_server
    http_server = HttpServerProcess(
        ip=get_driver().config.dict().get('record_http_ip', '127.0.0.1'),
        port=get_driver().config.dict().get('record_http_port', '8080'),
        output=queue
    )
    http_server.start()
    logger.info(f"Recorder Http Server Listening at: http://{http_server.ip}:{http_server.port}")


@get_driver().on_shutdown
def shutdown():
    os.kill(http_server.pid, signal.SIGINT)
    http_server.join()
