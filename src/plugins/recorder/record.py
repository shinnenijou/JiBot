import os
from threading import Thread, Event
import asyncio

from nonebot import logger, get_driver

import src.common.utils as utils

# Constant
TRANSCODE_FORMAT = 'mp4'


class Recorder(Thread):
    def __init__(self, streamer: str, live_url: str, out_path: str, running_flag: Event, notice_group: str, upload_to: str, options: dict[str, str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.streamer = streamer
        self.url: str = live_url
        self.path: str = out_path
        self.running_flag: Event = running_flag
        self.options: dict[str, str] = options
        self.notice_group = notice_group
        self.upload_to = upload_to

    def run(self):
        self.running_flag.set()

        logger.success(f'Start recording {self.path}')
        self.send_to_group(f"录像开始:\n{self.path}")

        cmds = ['streamlink', self.url, 'best', '-o', self.path]

        for k, v in self.options.items():
            cmds.append(k.strip())
            cmds.append(v.strip())

        os.system(' '.join(cmd for cmd in cmds))

        # 录像结束后即重置flag, 不等转码结束
        self.running_flag.clear()

        if not os.path.exists(self.path):
            logger.error("Recording failed.")
            return

        logger.success(f'{self.path} recording finished')

        # 发送群消息通知. 对录像文件进行一定的统计
        outbound_filename = self.path[self.path.rfind('/'):]
        size = os.path.getsize(outbound_filename) / (1 * 1024 * 1024)  # Mb
        self.send_to_group(f"录像完成:\n{outbound_filename}\nsize:{size} Mb")

        # 转码
        self.transcode()

    def transcode(self):
        index = self.path.rfind('.')

        if self.path[index + 1:] == TRANSCODE_FORMAT:
            return

        to_filename: str = self.self.path[:index] + TRANSCODE_FORMAT

        ffmpeg_bin = get_driver().config.dict().get('ffmpeg_bin', '/bin/ffmpeg')

        if not os.path.exists(ffmpeg_bin):
            logger.error("ffmpeg bin not found.")
            return

        cmds = [ffmpeg_bin, '-i', self.path, '-y',
                '-c:v', 'copy', '-c:a', 'copy', to_filename]

        if os.system(' '.join(cmd for cmd in cmds)) == 0:
            os.remove(self.path)
            self.path = to_filename
        elif os.path.exists(to_filename):
            os.remove(to_filename)

    def upload(self):
        if not self.upload_to:
            return

        rclone_bin = get_driver().config.dict().get('rclone_bin', '/bin/rclone')

        if not os.path.exists(rclone_bin):
            logger.error("rclone bin not found.")
            return

        filename = self.path[self.path.rfind('/'):]

        cmds = [rclone_bin, 'copyto', self.path,
                f'{self.upload_to}/{filename}']

        if os.system(' '.join(cmd for cmd in cmds)) == 0:
            self.send_to_group(f"上传成功:{filename}")

    def send_to_group(self, message: str):
        bot = utils.safe_get_bot()

        if bot is None:
            return

        asyncio.run(bot.send_group_msg(
            group_id=self.notice_group,
            message=message
        ))
