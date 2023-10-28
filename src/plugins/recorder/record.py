import os
from threading import Thread, Event

from nonebot import logger


class Recorder(Thread):
    def __init__(self, live_url: str, record_file: str, running_flag: Event, options: dict[str, str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.url: str = live_url
        self.filename: str = record_file
        self.running_flag: Event = running_flag
        self.options: dict[str, str] = options

    def run(self):
        self.running_flag.set()

        # TODO 录像开始时通知QQ群

        logger.success(f'Start recording {self.filename}')

        cmds = ['streamlink', self.url, 'best', '-s', '-o', self.filename]

        for k, v in self.options.items():
            cmds.append(k.strip())
            cmds.append(v.strip())

        os.system(' '.join(cmd for cmd in cmds))

        logger.success(f'{self.filename} recording finished')

        # 录像结束后即重置flag, 不等转码结束
        self.running_flag.clear()

        # TODO 录像结束时通知QQ群
