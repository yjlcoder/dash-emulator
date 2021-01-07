import asyncio
import time
from typing import Optional

from dash_emulator import logger, events, config

log = logger.getLogger(__name__)


class SpeedMonitor(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
            cls._instance.inited = False
        return cls._instance

    def __init__(self):
        if not self.inited:
            self.inited = True
            self.cfg = None

            self.avg_bandwidth = 0
            self.last_speed = -1

            self.downloaded = 0
            self.downloaded_before = 0
            self._calculate_speed_task = None  # type: Optional[asyncio.Task]

    async def calculate_speed(self):
        while True:
            downloaded = self.downloaded
            await asyncio.sleep(0.3)
            await self.feed(self.downloaded - downloaded, 0.3)
            self.print()

    def init(self, cfg):
        self.cfg = cfg  # type: config.Config
        event_bridge = events.EventBridge()

        async def calculate_speed():
            try:
                self._calculate_speed_task = asyncio.create_task(self.calculate_speed())
            except AttributeError:
                loop = asyncio.get_event_loop()
                self._calculate_speed_task = loop.create_task(self.calculate_speed())

        event_bridge.add_listener(events.Events.MPDParseComplete, calculate_speed)

        async def download_complete(*args, **kwargs):
            self.downloaded_before = self.downloaded

        event_bridge.add_listener(events.Events.SegmentDownloadComplete, download_complete)

    async def stop(self):
        self._calculate_speed_task.cancel()

    async def feed(self, data, time):
        if self.last_speed < 0:
            self.last_speed = data / time
            self.avg_bandwidth = self.last_speed
        else:
            self.last_speed = data / time
            self.avg_bandwidth = self.cfg.smoothing_factor * self.last_speed + (
                    1 - self.cfg.smoothing_factor) * self.avg_bandwidth

    def print(self):
        log.info("Avg bandwidth: %d bps" % (self.avg_bandwidth * 8))

    def get_speed(self):
        return self.avg_bandwidth


class BufferMonitor(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
            cls._instance.inited = False
        return cls._instance

    def __init__(self):
        if not self.inited:
            self.inited = True

            self.cfg = None

            self._buffer = 0

    def init(self, cfg):
        self.cfg = cfg

        async def feed_segment(duration, *args, **kwargs):
            self._buffer += duration
            await events.EventBridge().trigger(events.Events.BufferUpdated, buffer=self._buffer)

        events.EventBridge().add_listener(events.Events.SegmentDownloadComplete, feed_segment)

    @property
    def buffer(self):
        return self._buffer


class DownloadProgressMonitor(object):
    def __init__(self, cfg, session):
        self.segment_length = 0
        self.task = None  # type: asyncio.Task
        self.config = cfg
        self.downloaded = 0
        self.session = session

    async def start(self):
        """
        In MPEG-DASH, the player cannot download the segment completely, because of the bandwidth fluctuation
        :return: a coroutine object
        """
        bandwidth = SpeedMonitor().get_speed()
        length = self.segment_length
        timeout = length * 8 / bandwidth
        start_time = time.time()

        await asyncio.sleep(0.2)
        self.task.cancel()

        # while True:
        #     print("Downlaod task: %s, %d BETA Algorithm" % (self.task.get_name(), time.time()))
        #     await asyncio.sleep(0.1)
            # if time.time() - start_time > timeout * self.config.timeout_max_ratio:
            #     self.set_to_lowest_quaity = True
            #     self.task.cancel()
            #
            # downloaded = self.data_downloaded - self.data_downloaded_before_this_segment
            #
            # # f_i < f_i^{min}
            # if downloaded < self.config.min_frame_chunk_ratio * self.segment_content_length:
            #     # TODO
            #     pass
            # else:
            #     # f_i < f_i^{VQ}
            #     if downloaded < self.config.vq_threshold_size_ratio * self.segment_content_length:
            #         # TODO
            #         pass
            #
            # await asyncio.sleep(0.05)
