import os
from threading import Thread, Event
import asyncio

from nonebot import logger, get_driver

import src.common.utils as utils

# Constant
TRANSCODE_FORMAT = 'mp4'


class Recorder(Thread):
    def __init__(self, live_url: str, record_file: str, running_flag: Event, options: dict[str, str], notice_group: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.url: str = live_url
        self.filename: str = record_file
        self.running_flag: Event = running_flag
        self.options: dict[str, str] = options
        self.notice_group = notice_group

    def run(self):
        self.running_flag.set()

        logger.success(f'Start recording {self.filename}')
        self.send_to_group(f"录像开始:\n{self.filename}")

        cmds = ['streamlink', self.url, 'best', '-o', self.filename]

        for k, v in self.options.items():
            cmds.append(k.strip())
            cmds.append(v.strip())

        if os.system(' '.join(cmd for cmd in cmds)) != 0 or not os.path.exists(self.filename):
            self.running_flag.clear()
            logger.error("Recording failed.")
            return

        # 录像结束后即重置flag, 不等转码结束
        self.running_flag.clear()

        logger.success(f'{self.filename} recording finished')

        # 发送群消息通知. 对录像文件进行一定的统计
        outbound_filename = self.filename[self.filename.rfind('/'):]
        size = os.path.getsize(outbound_filename) / (1 * 1024 * 1024)  # Mb
        self.send_to_group(f"录像完成:\n{outbound_filename}\nsize:{size} Mb") 

        # 转码
        self.transcode()



    def transcode(self):
        index = self.filename.rfind('.')

        if self.filename[index + 1:] == TRANSCODE_FORMAT:
            return

        to_filename: str = self.self.filename[:index] + TRANSCODE_FORMAT

        ffmpeg_bin = get_driver().config.dict().get('ffmpeg_bin', '/bin/ffmpeg')
        
        if not os.path.exists(ffmpeg_bin):
            logger.error("ffmpeg bin not found.")
            return

        cmds = [ffmpeg_bin, '-i', self.filename, '-y',
                '-c:v', 'copy', '-c:a', 'copy', to_filename]

        if os.system(' '.join(cmd for cmd in cmds)) == 0:
            os.remove(self.filename)
        elif os.path.exists(to_filename):
            os.remove(to_filename)

    def send_to_group(self, message: str):
        bot = utils.safe_get_bot()

        if bot is None:
            return

        asyncio.run(bot.send_group_msg(
            group_id=self.notice_group,
            message=message
        ))
