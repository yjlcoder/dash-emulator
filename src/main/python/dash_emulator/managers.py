import asyncio
import csv
import pathlib
import signal
import subprocess
import sys
import time
from typing import Optional, List, Tuple

import aiohttp
import matplotlib.pyplot as plt
from dash_emulator import logger, events, abr, mpd, monitor, config

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
            # Flag shows if the singleton has been initialized
            self.inited = True

            # Properties for configurations
            self.cfg = None  # type: Optional[config.Config]

            # MPD parsed from the target URL
            self.mpd = None  # type: Optional[mpd.MPD]

            # Time
            self.playback_time = 0
            self.playback_start_realtime = 0

            # Asyncio Tasks
            self.task_check_buffer_sufficient = None  # type: Optional[asyncio.Task]
            self.task_update_playback_time = None  # type: Optional[asyncio.Task]

            # Playback Control
            self.abr_controller = None  # type: Optional[abr.ABRController]
            self.state = PlayManager.State.READY

            # The representations index of current playback
            self.current_video_representation_ind = -1
            self.current_audio_representation_ind = -1

            # Statistical_data
            self._bandwidth_segmentwise = {}

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
        return (monitor.BufferMonitor().buffer - self.playback_time) * 1000

    async def check_buffer_sufficient(self):
        while True:
            if self.buffer_level > 0:
                log.info("Buffer level sufficient: %.1f seconds" % (self.buffer_level / 1000))
                await asyncio.sleep(min(1, self.buffer_level / 1000))
            else:
                break
        if self.mpd.mediaPresentationDuration <= self.playback_time:
            await events.EventBridge().trigger(events.Events.End)
        else:
            await events.EventBridge().trigger(events.Events.Stall)

    async def update_current_time(self):
        while True:
            await asyncio.sleep(self.cfg.update_interval)
            self.playback_time += self.cfg.update_interval

    def init(self, cfg, mpd):
        self.cfg = cfg  # type: config.Config
        self.mpd = mpd

        self.abr_controller = abr.ABRController()

        # Play immediately
        async def can_play():
            log.info("The player is ready to play")
            await events.EventBridge().trigger(events.Events.Play)

        events.EventBridge().add_listener(events.Events.CanPlay, can_play)

        async def play():
            log.info("Video playback started")
            self.playback_start_realtime = time.time()

            try:
                self.task_update_playback_time = asyncio.create_task(self.update_current_time())
            except AttributeError:
                loop = asyncio.get_event_loop()
                self.task_update_playback_time = loop.create_task(self.update_current_time())

            try:
                self.task_check_buffer_sufficient = asyncio.create_task(self.check_buffer_sufficient())
            except AttributeError:
                loop = asyncio.get_event_loop()
                self.task_check_buffer_sufficient = loop.create_task(self.check_buffer_sufficient())
            self.switch_state("PLAYING")

        events.EventBridge().add_listener(events.Events.Play, play)

        async def stall():
            if self.task_update_playback_time is not None:
                self.task_update_playback_time.cancel()
            if self.task_check_buffer_sufficient is not None:
                self.task_check_buffer_sufficient.cancel()

            log.debug("Stall happened")
            self.switch_state("STALLING")
            before_stall = time.time()
            while True:
                await asyncio.sleep(self.cfg.update_interval)
                if monitor.BufferMonitor().buffer - self.playback_time > self.mpd.minBufferTime:
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
            # Save some statistical data
            self.save_statistical_data()

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

        async def ctrl_c_handler():
            print("Fast-forward to the end")
            # Change current time to 0.5 seconds before the end
            self.playback_time = monitor.BufferMonitor().buffer - 0.5
            asyncio.get_event_loop().remove_signal_handler(signal.SIGINT)

        async def download_end():
            await monitor.SpeedMonitor().stop()
            await asyncio.sleep(0.5)

            loop = asyncio.get_event_loop()
            if sys.version_info.minor < 7:
                loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(ctrl_c_handler()))
            else:
                loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(ctrl_c_handler()))
            print("You can press Ctrl-C to fastforward to the end of playback")

        events.EventBridge().add_listener(events.Events.DownloadEnd, download_end)

        async def plot():
            output_folder = self.cfg.args['output'] + "/figures/" or "./figures/"
            output_folder = pathlib.Path(output_folder).absolute()
            output_folder.mkdir(parents=True, exist_ok=True)

            # Durations of segments
            durations = DownloadManager().representation.durations
            start_num = DownloadManager().representation.startNumber
            fig = plt.figure()
            plt.plot([i for i in range(start_num, len(durations))], durations[start_num:])
            plt.xlabel("Segments")
            plt.ylabel("Durations (sec)")
            plt.title("Durations of each segment")
            fig.savefig(str(output_folder / "segment-durations.pdf"))
            plt.close()

            # Download bandwidth of each segment
            fig = plt.figure()
            inds = [i for i in sorted(self._bandwidth_segmentwise.keys())]
            bws = [self._bandwidth_segmentwise[i] for i in inds]
            plt.plot(inds, bws)
            plt.xlabel("Segments")
            plt.ylabel("Bandwidth (bps)")
            plt.title("Bandwidth of downloading each segment")
            fig.savefig(str(output_folder / "segment-download-bandwidth.pdf"))
            plt.close()

        async def exit_program():
            print("Prepare to exit the program")
            events.EventBridge().over = True

        async def validate_output_path() -> None:
            """
            This function is used to validate the output path
            It will create the folder if it doesn't exist
            It will prompt a message to ask for deleting everything in the folder
            """
            output_path = self.cfg.args['output']
            path = pathlib.Path(output_path)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            files = [i for i in path.glob("*")]
            delete_choice = self.cfg.args['y']
            if len(files) > 0:
                delete_choice = delete_choice or (
                        input(
                            "Existing files are detected in the output folder. Do you want to delete files before transcoding? (y/N)") == 'y')
            if delete_choice:
                # shutil.rmtree(path.absolute())
                subprocess.call(['rm', '-rf', str(path) + "/*"])
                path.mkdir(parents=True, exist_ok=True)

        async def output() -> None:
            """
            Generate output reports and videos
            """
            log.info("Streaming ended.")
            await validate_output_path()
            output_path = self.cfg.args['output']

            # Reports
            seg_inds = [i for i in sorted(self._bandwidth_segmentwise.keys())]
            bws = [self._bandwidth_segmentwise[i] for i in seg_inds]
            with open(output_path + '/results.csv', 'w') as f:
                writer = csv.DictWriter(f, fieldnames=["index", "filename", "init_name", "avg_bandwidth", "bitrate",
                                                       "width", "height", "mime", "codec"])
                writer.writeheader()
                for (segment_name, representation), ind, bw in zip(DownloadManager().download_record, seg_inds, bws):
                    record = {
                        "index": ind,
                        "filename": segment_name,
                        "init_name": representation.init_filename,
                        "avg_bandwidth": bw,
                        "bitrate": representation.bandwidth,
                        "width": representation.width,
                        "height": representation.height,
                        "mime": representation.mime,
                        "codec": representation.codec
                    }
                    writer.writerow(record)
                log.info(f"Done Writing to {output_path + '/results.csv'}")

        if self.cfg.args['output'] is not None:
            events.EventBridge().add_listener(events.Events.End, output)
        if self.cfg.args['plot']:
            events.EventBridge().add_listener(events.Events.End, plot)
        events.EventBridge().add_listener(events.Events.End, exit_program)

    def save_statistical_data(self):
        # Bandwidth for each segment
        video_ind = DownloadManager().video_ind
        speed = monitor.SpeedMonitor().get_speed()
        self._bandwidth_segmentwise[video_ind] = speed


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

            # This property records all downloaded segments and its corresponding representation
            # Each tuple in the list represents a segment
            # Each tuple contains 2 elements: filename of the segment, corresponding representation
            self.download_record = []  # type: List[Tuple[str, mpd.Representation]]

    async def download(self, url) -> None:
        """
        Download the file of url and save it if `output` shows in the args
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.segment_length = resp.headers["Content-Length"]
                while True:
                    chunk = await resp.content.read(self.cfg.chunk_size)
                    if not chunk:
                        break
                    monitor.SpeedMonitor().downloaded += (len(chunk) * 8)

    def init(self, cfg: config.Config, mpd: mpd.MPD) -> None:
        """
        Init the download manager, including add callbacks to events
        """
        self.cfg = cfg
        self.mpd = mpd

        async def start_download():
            if self.video_ind >= len(self.representation.urls):
                await events.EventBridge().trigger(events.Events.DownloadEnd)
                return
            # If the init file hasn't been downloaded for this representation, download that first
            if not self.representation.is_inited:
                url = self.representation.initialization

                try:
                    task = asyncio.create_task(self.download(url))
                except AttributeError:
                    loop = asyncio.get_event_loop()
                    task = loop.create_task(self.download(url))

                await task
                self.representation.is_inited = True
                self.representation.init_filename = url.split('/')[-1]
                await events.EventBridge().trigger(events.Events.InitializationDownloadComplete)
                log.info("Download initialization for representation %s" % self.representation.id)

            # Download the segment
            url = self.representation.urls[self.video_ind]
            try:
                task = asyncio.create_task(self.download(url))
            except AttributeError:
                loop = asyncio.get_event_loop()
                task = loop.create_task(self.download(url))

            # Add segment to download record
            self.download_record.append((url.split('/')[-1], self.representation))

            await task
            await events.EventBridge().trigger(events.Events.DownloadComplete)
            log.info("Download one segment: representation %s (%d bps), segment %d" % (
                self.representation.id, self.representation.bandwidth, self.video_ind))

        events.EventBridge().add_listener(events.Events.DownloadStart, start_download)
