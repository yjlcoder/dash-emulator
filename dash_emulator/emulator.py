from typing import Optional, Dict

import requests

from dash_emulator import arguments, mpd, config, logger, abr, monitor

log = logger.getLogger(__name__)


class Emulator():
    def __init__(self, args):
        self.args = args  # type: Dict[str, str]
        self.config = config.Config(args)
        self.mpd = None  # type: Optional[mpd.MPD]

    def start(self):
        target: str = self.args[arguments.PLAYER_TARGET]  # MPD file link
        mpd_content: str = requests.get(target).text
        self.mpd = mpd.MPD(mpd_content, target)

        speedMonitor = monitor.SpeedMonitor()
        abrController = abr.ABRController(self.mpd, speedMonitor, self.config)

        # video
        representation = abrController.choose("video")
        urls = representation.urls
        init_url = representation.initialization
