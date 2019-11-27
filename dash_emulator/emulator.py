import asyncio
from typing import Optional, Dict

import aiohttp
import requests

from dash_emulator import arguments, mpd, config, logger, abr, monitor

log = logger.getLogger(__name__)


class Emulator():
    async def download_segment(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break
                    self.data_downloaded += len(chunk)

    async def feed_speed_monitor(self):
        while True:
            data_previous = self.data_downloaded
            await asyncio.sleep(1)
            diff = self.data_downloaded - data_previous
            await self.speed_monitor.feed(diff, 1)
            self.speed_monitor.print()

    def __init__(self, args):
        self.args = args  # type: Dict[str, str]
        self.config = config.Config(args)
        self.mpd = None  # type: Optional[mpd.MPD]

        self.speed_monitor = None  # type: Optional[monitor.SpeedMonitor]
        self.abr_controller = None  # type: Optional[abr.ABRController]

        self.data_downloaded = 0

    async def start(self):
        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
        self.mpd = mpd.MPD(mpd_content, target)

        self.speed_monitor = monitor.SpeedMonitor(self.config)
        self.abr_controller = abr.ABRController(self.mpd, self.speed_monitor, self.config)

        feed_speed_monitor_task = asyncio.create_task(self.feed_speed_monitor())

        # video
        representation = self.abr_controller.choose("video")
        ind = representation.startNumber

        while ind < len(representation.urls):
            representation = self.abr_controller.choose("video")
            if not representation.is_inited:
                url = representation.initialization
                task = asyncio.create_task(self.download_segment(url))
                await task
                print("Download initialzation for representation %s" % representation.id)
                representation.is_inited = True

            url = representation.urls[ind]
            task = asyncio.create_task(self.download_segment(url))

            await task
            print("Download one segment: representation %s, segment %d" % (representation.id, ind))
            ind += 1

        feed_speed_monitor_task.cancel()
