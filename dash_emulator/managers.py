import asyncio
import time
from typing import Optional

import aiohttp

from dash_emulator import events, monitor, mpd, config, logger, abr

log = logger.getLogger(__name__)


class PlayManager(object):
    class State:
        READY = 0
        PLAYING = 1
        STALLING = 2
        STOPPED = 3

    _instance = None

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

            self.abr_controller = None  # type: Optional[abr.ABRController]
            self.state = PlayManager.State.READY

            self.current_video_representation_ind = -1
            self.current_audio_representation_ind = -1

    def switch_state(self, state):
        if state == "READY" or state == PlayManager.State.READY:
            self.state = PlayManager.State.READY
        elif state == "PLAYING" or state == PlayManager.State.PLAYING:
            self.state = PlayManager.State.PLAYING
        elif state == "STALLING" or state == PlayManager.State.STALLING:
            self.state = PlayManager.State.STALLING
        elif state == "STOPPED" or state == PlayManager.State.STOPPED:
            self.state = PlayManager.State.STOPPED
        else:
            log.error("Unknown State: %s" % state)

    @property
    def ready(self):
        return self.state == PlayManager.State.READY

    @property
    def playing(self):
        return self.state == PlayManager.State.PLAYING

    @property
    def stalling(self):
        return self.state == PlayManager.State.STALLING

    @property
    def stopped(self):
        return self.state == PlayManager.State.STOPPED

    @property
    def buffer_level(self):
        return (monitor.BufferMonitor().buffer - self.current_time) * 1000

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

        self.abr_controller = abr.ABRController()

        # Play immediately
        async def can_play():
            log.info("The player is ready to play")
            await events.EventBridge().trigger(events.Events.Play)

        events.EventBridge().add_listener(events.Events.CanPlay, can_play)

        async def play():
            log.info("Video playback started")
            self.start_time = time.time()

            try:
                self.update_current_time_task = asyncio.create_task(self.update_current_time())
            except AttributeError:
                loop = asyncio.get_event_loop()
                self.update_current_time_task = loop.create_task(self.update_current_time())

            try:
                self.check_buffer_sufficient_task = asyncio.create_task(self.check_buffer_sufficient())
            except AttributeError:
                loop = asyncio.get_event_loop()
                self.check_buffer_sufficient_task = loop.create_task(self.check_buffer_sufficient())
            self.switch_state("PLAYING")

        events.EventBridge().add_listener(events.Events.Play, play)

        async def stall():
            if self.update_current_time_task is not None:
                self.update_current_time_task.cancel()
            if self.check_buffer_sufficient_task is not None:
                self.check_buffer_sufficient_task.cancel()

            log.debug("Stall happened")
            self.switch_state("STALLING")
            before_stall = time.time()
            while True:
                await asyncio.sleep(self.cfg.update_interval)
                if monitor.BufferMonitor().buffer - self.current_time > self.mpd.minBufferTime:
                    break
            log.debug("Stall ends, duration: %.3f" % (time.time() - before_stall))
            await events.EventBridge().trigger(events.Events.Play)

        events.EventBridge().add_listener(events.Events.Stall, stall)

        async def download_start():
            self.current_video_representation_ind = self.abr_controller.choose("video")
            DownloadManager().representation = self.mpd.videoAdaptationSet.representations[
                self.current_video_representation_ind]
            DownloadManager().video_ind = DownloadManager().representation.startNumber
            await events.EventBridge().trigger(events.Events.DownloadStart)

        events.EventBridge().add_listener(events.Events.MPDParseComplete, download_start)

        async def download_next():
            monitor.BufferMonitor().feed_segment(
                DownloadManager().representation.durations[DownloadManager().video_ind])
            log.info("Current Buffer Level: %.3f" % self.buffer_level)
            self.current_video_representation_ind = self.abr_controller.choose('video')
            DownloadManager().representation = self.mpd.videoAdaptationSet.representations[
                self.current_video_representation_ind]
            DownloadManager().video_ind += 1
            await events.EventBridge().trigger(events.Events.DownloadStart)

        async def check_canplay():
            if self.ready and self.buffer_level > self.mpd.minBufferTime:
                await events.EventBridge().trigger(events.Events.CanPlay)

        events.EventBridge().add_listener(events.Events.DownloadComplete, download_next)
        events.EventBridge().add_listener(events.Events.DownloadComplete, check_canplay)


class DownloadManager(object):
    _instance = None

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

            self.video_ind = None
            self.audio_ind = None

            self.abr_controller = None
            self.segment_length = None

            self.representation = None  # type: Optional[mpd.Representation]

    async def download(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.segment_length = resp.headers["Content-Length"]
                while True:
                    chunk = await resp.content.read(self.cfg.chunk_size)
                    if not chunk:
                        break
                    monitor.SpeedMonitor().downloaded += (len(chunk) * 8)

    def init(self, cfg, mpd):
        self.cfg = cfg
        self.mpd = mpd

        async def start_download():
            if self.video_ind >= len(self.representation.urls):
                await events.EventBridge().trigger(events.Events.DownloadEnd)
                return
            if not self.representation.is_inited:
                url = self.representation.initialization

                task = None
                try:
                    task = asyncio.create_task(self.download(url))
                except AttributeError:
                    loop = asyncio.get_event_loop()
                    task = loop.create_task(self.download(url))

                await task
                self.representation.is_inited = True
                await events.EventBridge().trigger(events.Events.InitializationDownloadComplete)
                log.info("Download initialization for representation %s" % self.representation.id)

            url = self.representation.urls[self.video_ind]

            task = None
            try:
                task = asyncio.create_task(self.download(url))
            except AttributeError:
                loop = asyncio.get_event_loop()
                task = loop.create_task(self.download(url))

            await task
            await events.EventBridge().trigger(events.Events.DownloadComplete)
            log.info("Download one segment: representation %s, segment %d" % (self.representation.id, self.video_ind))

        events.EventBridge().add_listener(events.Events.DownloadStart, start_download)
