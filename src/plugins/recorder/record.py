import os
from threading import Thread, Event
import asyncio
import aiohttp

from nonebot import logger, get_driver

import src.common.utils as utils


# Constant
RECORD_FORMAT = 'ts'
TRANSCODE_FORMAT = 'mp4'


def upload(upload_to, path):
    if not upload_to:
        return

    rclone_bin = get_driver().config.dict().get('rclone_bin', '/bin/rclone')

    if not os.path.exists(rclone_bin):
        logger.error("rclone bin not found.")
        return

    logger.info(f"Try to Upload: {path}")

    filename = path[path.rfind('/'):]

    cmds = [rclone_bin, 'copyto', path,
            f'{upload_to}/{filename}']

    os.system(' '.join(cmd for cmd in cmds))


def send_to_bark(message: str):
    """
    将消息推送至Bark
    """
    bark_url = get_driver().config.dict().get('bark_url', '')

    if not bark_url:
        return

    async def _send_to_bark(message: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f"{bark_url}/JiBot/{message}") as resp:
                await resp.json()

    try:
        asyncio.run(_send_to_bark(message))
    except Exception as e:
        logger.error(f"Send message error: {str(e)}")


class Recorder(Thread):
    def __init__(self, streamer: str, live_url: str, out_path: str, running_flag: Event, notice_group: str, upload_to: str, options: dict[str, str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.streamer = streamer
        self.url: str = live_url
        self.path: str = f"{out_path}.{RECORD_FORMAT}"
        self.running_flag: Event = running_flag
        self.options: dict[str, str] = options
        self.notice_group = notice_group
        self.upload_to = upload_to

    def run(self):
        self.running_flag.set()

        logger.info(f'Start recording {self.path}')

        cmds = ['streamlink', self.url, 'best', '-o', self.path]

        for k, v in self.options.items():
            if isinstance(v, str):
                cmds.append(k.strip())
                cmds.append(v.strip())
            elif isinstance(v, list):
                for value in v:
                    cmds.append(k.strip())
                    cmds.append(value.strip())

        os.system(' '.join(cmd for cmd in cmds))

        # 录像结束后即重置flag, 不等转码结束
        self.running_flag.clear()

        if not os.path.exists(self.path):
            logger.error("Recording failed.")
            return

        logger.success(f'{self.path} recording finished')

        # 转码
        self.transcode()

        # 发送群消息通知. 对录像文件进行一定的统计
        filename = self.path[self.path.rfind('/'):]
        size = os.path.getsize(self.path) / (1 * 1024 * 1024)
        self.send_to_group(f"录像完成:\n{filename}\nsize:{size:.1f} Mb")
        send_to_bark(f"录像完成:\n{filename}\nsize:{size:.1f} Mb")

        # 上传
        self.upload()

    def transcode(self):
        index = self.path.rfind('.')

        if self.path[index + 1:] == TRANSCODE_FORMAT:
            return

        to_filename: str = f"{self.path[:index]}.{TRANSCODE_FORMAT}"

        ffmpeg_bin = get_driver().config.dict().get('ffmpeg_bin', '/bin/ffmpeg')

        if not os.path.exists(ffmpeg_bin):
            logger.error("ffmpeg bin not found.")
            return

        logger.info(f"Try to Transcode: {self.path}")

        cmds = [ffmpeg_bin, '-i', self.path, '-y',
                '-c:v', 'copy', '-c:a', 'copy', to_filename]

        if os.system(' '.join(cmd for cmd in cmds)) == 0 and os.path.exists(to_filename):
            os.remove(self.path)
            self.path = to_filename
        elif os.path.exists(to_filename):
            os.remove(to_filename)

    def upload(self):
        upload(self.upload_to, self.path)

    def send_to_group(self, message: str):
        bot = utils.safe_get_bot()

        if bot is None:
            return

        try:
            asyncio.run(bot.send_group_msg(
                group_id=self.notice_group,
                message=message
            ))
        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
    


