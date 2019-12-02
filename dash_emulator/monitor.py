import asyncio

from dash_emulator import config, logger, events, managers

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
                asyncio.create_task(self.calculate_speed())
            except AttributeError:
                loop = asyncio.get_event_loop()
                loop.create_task(self.calculate_speed())

        event_bridge.add_listener(events.Events.MPDParseComplete, calculate_speed)

        async def download_complete():
            self.downloaded_before = self.downloaded

        event_bridge.add_listener(events.Events.DownloadComplete, download_complete)
        event_bridge.add_listener(events.Events.InitializationDownloadComplete, download_complete)

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

    @property
    def buffer(self):
        return self._buffer

    def feed_segment(self, duration):
        self._buffer += duration
