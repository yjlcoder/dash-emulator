import asyncio
import time
from typing import Optional, Dict

import requests

from dash_emulator import logger, arguments, events, abr, mpd, monitor, config, managers

log = logger.getLogger(__name__)


class Emulator():
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
        # Init the event bridge as a new thread
        event_thread = events.EventBridge()
        await event_thread.init_queue()
        # event_thread.start()

        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
        self.mpd = mpd.MPD(mpd_content, target)

        # Init the play manager
        play_manager = managers.PlayManager()
        play_manager.init(self.config, self.mpd)

        # Init the download manager
        download_manager = managers.DownloadManager()
        download_manager.init(self.config)

        self.abr_controller = abr.ABRController()
        self.abr_controller.init(self.config, abr.SRDDashVideoABR())

        await events.EventBridge().trigger(events.Events.MPDParseComplete)
        await event_thread.listen()
