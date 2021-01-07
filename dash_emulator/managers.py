import asyncio
import csv
import os
import pathlib
import random
import signal
import subprocess
import sys
import time
from typing import Optional, Dict

import aiohttp
import matplotlib.pyplot as plt

from dash_emulator import logger, events, abr, mpd, monitor, config
from dash_emulator.monitor import DownloadProgressMonitor

log = logger.getLogger(__name__)


class PlayManager(object):
    class State:
        READY = 0
        PLAYING = 1
        STALLING = 2
        STOPPED = 3

    _instance = None

    class DownloadTaskSession(object):
        session_id = 1

        def __init__(self, adaptation_set, url, next_task=None, duration: float = 0, representation_indices=None):
            self.session_id = PlayManager.DownloadTaskSession.session_id
            PlayManager.DownloadTaskSession.session_id += 1
            self.adaptation_set = adaptation_set  # type: mpd.AdaptationSet
            self.url = url
            self.next_task = next_task
            self.duration = duration
            self.representation_indices = representation_indices

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

            # The representations index of current playback. Key: adaptation set id, value: representation index
            self.representation_indices = dict()  # type: Dict[str, int]

            # Statistical_data
            self._bandwidth_segmentwise = {}

            # Download task sessions
            self.download_task_sessions = dict()  # type: Dict[str, PlayManager.DownloadTaskSession]

            # Current downloading segment index
            self.segment_index = 0

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

    def clear_download_task_sessions(self):
        self.download_task_sessions.clear()

    def create_session_urls(self):
        """
        Create download_task_sessions for current segment_index
        :return:
        """
        for adaptation_set in self.mpd.adaptationSets.values():
            representation_index = self.representation_indices[adaptation_set.id]
            representation = adaptation_set.representations[representation_index]
            segment_number = self.segment_index + representation.startNumber
            segment_download_session = PlayManager.DownloadTaskSession(adaptation_set,
                                                                       representation.urls[segment_number], None,
                                                                       representation.durations[segment_number],
                                                                       self.representation_indices
                                                                       )
            if not representation.is_inited:
                init_download_session = PlayManager.DownloadTaskSession(adaptation_set,
                                                                        representation.initialization_url,
                                                                        segment_download_session, 0,
                                                                        self.representation_indices)
                representation.is_inited = True
                self.download_task_sessions[adaptation_set.id] = init_download_session
            else:
                self.download_task_sessions[adaptation_set.id] = segment_download_session

    def init(self, cfg, mpd: mpd.MPD):
        self.cfg = cfg  # type: config.Config
        self.mpd = mpd

        for adaptation_set in mpd.adaptationSets.values():
            self.representation_indices[adaptation_set.id] = -1  # Init the representation of each adaptation set to -1

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
            # Start downloading all adaptation sets
            self.representation_indices = self.abr_controller.calculate_next_segment(monitor.SpeedMonitor().get_speed(),
                                                                                     self.segment_index,
                                                                                     self.representation_indices,
                                                                                     self.mpd.adaptationSets)
            self.create_session_urls()

            for adaptation_set_id, session in self.download_task_sessions.items():
                await events.EventBridge().trigger(events.Events.DownloadStart, session=session)

        events.EventBridge().add_listener(events.Events.MPDParseComplete, download_start)

        async def download_next(session: PlayManager.DownloadTaskSession, *args, **kwargs):
            if session.next_task is None:
                del self.download_task_sessions[session.adaptation_set.id]
            else:
                self.download_task_sessions[session.adaptation_set.id] = session.next_task
                await events.EventBridge().trigger(events.Events.DownloadStart, session=session.next_task)
                return
            if len(self.download_task_sessions) == 0:
                await events.EventBridge().trigger(events.Events.SegmentDownloadComplete,
                                                   segment_index=self.segment_index, duration=session.duration)
                self.segment_index += 1
                self.representation_indices = self.abr_controller.calculate_next_segment(
                    monitor.SpeedMonitor().get_speed(),
                    self.segment_index,
                    self.representation_indices,
                    self.mpd.adaptationSets)
                try:
                    self.create_session_urls()
                except IndexError as e:
                    await events.EventBridge().trigger(events.Events.DownloadEnd)
                else:
                    for adaptation_set_id, session in self.download_task_sessions.items():
                        await events.EventBridge().trigger(events.Events.DownloadStart, session=session)

        async def check_canplay(*args, **kwargs):
            if self.ready and self.buffer_level > self.mpd.minBufferTime:
                await events.EventBridge().trigger(events.Events.CanPlay)

        events.EventBridge().add_listener(events.Events.DownloadComplete, download_next)
        events.EventBridge().add_listener(events.Events.BufferUpdated, check_canplay)

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

        async def buffer_updated(buffer, *args, **kwargs):
            log.info("Current Buffer Level: %.3f" % self.buffer_level)

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
                        input("Do you want to delete files in the output folder? (y/N)") == 'y')
            if delete_choice:
                # shutil.rmtree(path.absolute())
                subprocess.call(['rm', '-rf', str(path) + "/*"])
                path.mkdir(parents=True, exist_ok=True)

        async def output() -> None:
            """
            Generate output reports and videos
            """
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

                # Merge segments into a complete one
                tmp_output_path = '/tmp/playback-merge-%05d' % random.randint(1, 99999)
                os.mkdir(tmp_output_path)
                segment_list_file = '%s/%s' % (tmp_output_path, 'segment-list.txt')
                target_output_path = "%s/%s" % (output_path, 'playback.mp4')

                for (segment_name, representation), ind, bw in zip(DownloadManager().download_record, seg_inds, bws):
                    with open('%s/%s' % (output_path, 'merge-segment-%d.mp4' % ind), 'wb') as f:
                        subprocess.call(['cat', "%s/%s" % (output_path, representation.init_filename),
                                         "%s/%s" % (output_path, segment_name)], stdout=f)
                    tmp_segment_path = '%s/segment-%d.mp4' % (tmp_output_path, ind)
                    subprocess.call(
                        ['ffmpeg', '-i', "%s/%s" % (output_path, 'merge-segment-%d.mp4' % ind), '-vcodec', 'libx264',
                         '-vf', 'scale=1920:1080', tmp_segment_path], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
                    with open(segment_list_file, 'a') as f:
                        subprocess.call(['echo', 'file %s' % tmp_segment_path], stdout=f)
                        f.flush()

            print(target_output_path)
            subprocess.call(
                ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', segment_list_file, '-c', 'copy', target_output_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if self.cfg.args['output'] is not None:
            events.EventBridge().add_listener(events.Events.End, output)
        if self.cfg.args['plot']:
            events.EventBridge().add_listener(events.Events.End, plot)
        events.EventBridge().add_listener(events.Events.End, exit_program)


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

    async def download(self, url, download_progress_monitaor) -> None:
        """
        Download the file of url and save it if `output` shows in the args
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                output = self.cfg.args['output']
                if output is not None:
                    f = open(output + '/' + url.split('/')[-1], 'wb')
                download_progress_monitaor.segment_length = resp.headers["Content-Length"]
                while True:
                    chunk = await resp.content.read(self.cfg.chunk_size)
                    if not chunk:
                        if output is not None:
                            f.close()
                        break
                    monitor.SpeedMonitor().downloaded += (len(chunk) * 8)
                    download_progress_monitaor.downloaded += len(chunk)
                    if output is not None:
                        f.write(chunk)

    def init(self, cfg: config.Config) -> None:
        """
        Init the download manager, including add callbacks to events
        """
        self.cfg = cfg

        async def start_download(session: PlayManager.DownloadTaskSession):
            # if self.segment_index >= self.segment_num:
            #     await events.EventBridge().trigger(events.Events.DownloadEnd)
            #     return

            # If the init file hasn't been downloaded for this representation, download that first

            # if not self.representation.is_inited:
            #     url = self.representation.initialization
            #
            #     try:
            #         task = asyncio.create_task(self.download(url))
            #     except AttributeError:
            #         loop = asyncio.get_event_loop()
            #         task = loop.create_task(self.download(url))
            #
            #     await task
            #     self.representation.is_inited = True
            #     self.representation.init_filename = url.split('/')[-1]
            #     await events.EventBridge().trigger(events.Events.InitializationDownloadComplete)
            #     log.info("Download initialization for representation %s" % self.representation.id)

            url = session.url

            assert url is not None

            download_progress_monitor = DownloadProgressMonitor(self.cfg, session)

            # Download the segment
            try:
                task = asyncio.create_task(self.download(url, download_progress_monitor))
            except AttributeError:
                loop = asyncio.get_event_loop()
                task = loop.create_task(self.download(url, download_progress_monitor))

            download_progress_monitor.task = task

            try:
                monitor_task = asyncio.create_task(download_progress_monitor.start())  # type: asyncio.Task
            except AttributeError:
                loop = asyncio.get_event_loop()
                monitor_task = loop.create_task(download_progress_monitor.start())

            try:
                await task
            except asyncio.CancelledError:
                print("Partial Received")
            monitor_task.cancel()
            await events.EventBridge().trigger(events.Events.DownloadComplete, session=session)

        events.EventBridge().add_listener(events.Events.DownloadStart, start_download)
