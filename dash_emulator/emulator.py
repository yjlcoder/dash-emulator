import asyncio
import time
from typing import Optional, Dict

import requests

from dash_emulator import arguments, mpd, config, logger, abr, monitor, events, managers

log = logger.getLogger(__name__)


class Emulator():
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

        # Init the speed monitor
        speed_monitor = monitor.SpeedMonitor()  # type: monitor.SpeedMonitor
        speed_monitor.init(self.config)

        # Init the buffer monitor
        buffer_monitor = monitor.BufferMonitor()  # type: monitor.BufferMonitor
        buffer_monitor.init(self.config)

        self.abr_controller = None  # type: Optional[abr.ABRController]

        # Tasks
        # downloading task
        self.task = None  # type: Optional[asyncio.Task]
        self.segment_content_length = 0  # type: int

    async def start(self):
        # Init the event bridge
        event_thread = events.EventBridge()
        event_thread.start()

        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
        self.mpd = mpd.MPD(mpd_content, target)

        # Init the play manager
        play_manager = managers.PlayManager()
        play_manager.init(self.config, self.mpd)

        # Init the download manager
        download_manager = managers.DownloadManager()
        download_manager.init(self.config, self.mpd)

        self.abr_controller = abr.ABRController()
        self.abr_controller.init(self.mpd, monitor.SpeedMonitor(), self.config)

        await events.EventBridge().trigger(events.Events.MPDParseComplete)
