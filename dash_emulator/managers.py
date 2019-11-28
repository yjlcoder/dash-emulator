import asyncio
import time
from typing import Optional

from dash_emulator import events, monitor, mpd, config, logger

log = logger.getLogger(__name__)


class PlayManager(object):
    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
            cls._instance.inited = False
        return cls._instance

    def __init__(self):
        if not self.inited:
            self.inited = True

            self.cfg = None  # type: Optional[config.Config]
            self.mpd = None  # type: Optional[mpd.MPD]
            self.current_time = 0
            self.start_time = 0

            self.check_buffer_sufficient_task = None  # type: Optional[asyncio.Task]
            self.update_current_time_task = None  # type: Optional[asyncio.Task]

    @property
    def buffer_level(self):
        return self.current_time - monitor.BufferMonitor().buffer

    async def check_buffer_sufficient(self):
        while True:
            if monitor.BufferMonitor().buffer > self.current_time:
                await asyncio.sleep(monitor.BufferMonitor().buffer - self.current_time)
            else:
                break
        if self.mpd.mediaPresentationDuration <= self.current_time:
            await events.EventBridge().trigger(events.Events.End)
        else:
            await events.EventBridge().trigger(events.Events.Stall)

    async def update_current_time(self):
        while True:
            await asyncio.sleep(self.cfg.update_interval)
            self.current_time += self.cfg.update_interval

    def init(self, cfg, mpd):
        self.cfg = cfg
        self.mpd = mpd

        # Play immediately
        async def can_play():
            await events.EventBridge().trigger(events.Events.Play)

        events.EventBridge().add_listener(events.Events.CanPlay, can_play)

        async def play():
            self.start_time = time.time()
            self.update_current_time_task = asyncio.create_task(self.update_current_time())
            self.check_buffer_sufficient_task = asyncio.create_task(self.check_buffer_sufficient())

        events.EventBridge().add_listener(events.Events.Play, play)

        async def stall():
            if self.update_current_time_task is not None:
                self.update_current_time_task.cancel()
            if self.check_buffer_sufficient_task is not None:
                self.check_buffer_sufficient_task.cancel()

            log.debug("Stall happened")
            before_stall = time.time()
            while True:
                await asyncio.sleep(self.cfg.update_interval)
                if monitor.BufferMonitor().buffer - self.current_time > self.mpd.minBufferTime:
                    break
            log.debug("Stall ends, duration: %.3f" % (time.time() - before_stall))
            await events.EventBridge().trigger(events.Events.Play)

        events.EventBridge().add_listener(events.Events.Stall, stall)
