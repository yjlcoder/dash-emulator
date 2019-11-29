import asyncio
import time
from typing import Optional, Dict

import aiohttp
import requests

from dash_emulator import arguments, mpd, config, logger, abr, monitor, events

log = logger.getLogger(__name__)


class Emulator():
    async def download_segment(self, url):
        """
        :param url: segment url (target) to download
        :return: a coroutine object
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.segment_content_length = resp.headers["Content-Length"]
                while True:
                    chunk = await resp.content.read(40960)
                    if not chunk:
                        break
                    monitor.SpeedMonitor().downloaded += len(chunk)

    async def download_progress_monitor(self):
        """
        In MPEG-DASH, the player cannot download the segment completely, because of the bandwidth fluctuation
        :return: a coroutine object
        """
        bandwidth = self.speed_monitor.get_speed()
        length = self.segment_content_length
        timeout = length * 8 / bandwidth
        start_time = time.time()

        await asyncio.sleep(timeout)

        while True:
            if time.time() - start_time > timeout * self.config.timeout_max_ratio:
                self.set_to_lowest_quaity = True
                self.task.cancel()

            downloaded = self.data_downloaded - self.data_downloaded_before_this_segment

            # f_i < f_i^{min}
            if downloaded < self.config.min_frame_chunk_ratio * self.segment_content_length:
                # TODO
                pass
            else:
                # f_i < f_i^{VQ}
                if downloaded < self.config.vq_threshold_size_ratio * self.segment_content_length:
                    # TODO
                    pass

            await asyncio.sleep(0.05)

    def __init__(self, args):
        self.args = args  # type: Dict[str, str]
        self.config = config.Config(args)
        self.mpd = None  # type: Optional[mpd.MPD]

        speed_monitor = monitor.SpeedMonitor()  # type: monitor.SpeedMonitor
        speed_monitor.init(self.config)

        buffer_monitor = monitor.BufferMonitor()  # type: monitor.BufferMonitor
        buffer_monitor.init(self.config)

        self.abr_controller = None  # type: Optional[abr.ABRController]

        self.set_to_lowest_quaity = False

        # Tasks
        # downloading task
        self.task = None  # type: Optional[asyncio.Task]
        self.segment_content_length = 0  # type: int
        # task to feed speed into speed monitor
        self.feed_speed_monitor_task = None  # type: Optional[asyncio.Task]

    async def start(self):
        event_thread = events.EventBridge()
        event_thread.start()

        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
        self.mpd = mpd.MPD(mpd_content, target)

        await events.EventBridge().trigger(events.Events.MPDParseComplete)

        self.abr_controller = abr.ABRController(self.mpd, monitor.SpeedMonitor(), self.config)

        # video
        representation = self.abr_controller.choose("video")
        ind = representation.startNumber

        while ind < len(representation.urls):

            representation = self.abr_controller.choose("video")
            if not representation.is_inited:
                url = representation.initialization
                self.task = asyncio.create_task(self.download_segment(url))
                await self.task
                self.task = None
                log.info("Download initialzation for representation %s" % representation.id)
                representation.is_inited = True

            url = representation.urls[ind]
            self.task = asyncio.create_task(self.download_segment(url))

            await self.task
            self.task = None

            monitor.BufferMonitor().feed_segment(representation.durations[ind])
            await events.EventBridge().trigger(events.Events.DownloadComplete)
            log.info("Download one segment: representation %s, segment %d" % (representation.id, ind))
            log.info("Buffer level: %.3f" % monitor.BufferMonitor().buffer)
            ind += 1

        self.feed_speed_monitor_task.cancel()
