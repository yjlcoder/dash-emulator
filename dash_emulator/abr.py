from typing import Optional

from dash_emulator import monitor, config, mpd, logger

log = logger.getLogger(__name__)


class ABRController(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
            cls._instance.inited = False
        return cls._instance

    def __init__(self):
        if not self.inited:
            self.inited = True
            self.mpd = None  # type: Optional[mpd.MPD]
            self.speed_monitor = None
            self.cfg = None

            self.video_chosen = -1
            self.audio_chosen = -1

    def init(self, mpd_obj: mpd.MPD, speed_monitor: monitor.SpeedMonitor, cfg: config.Config):
        self.mpd = mpd_obj
        self.speed_monitor = speed_monitor
        self.cfg = cfg

    def choose(self, type) -> mpd.Representation:
        # TODO: change this
        if type == 'video':
            if len(self.mpd.videoAdaptationSet.representations) > 0:
                self.video_chosen = (self.video_chosen + 1) % len(self.mpd.videoAdaptationSet.representations)
                return self.mpd.videoAdaptationSet.representations[self.video_chosen]
            else:
                return None
        elif type == 'audio':
            if len(self.mpd.videoAdaptationSet.representations) > 0:
                return self.mpd.audioAdaptationSet.representations[0]
            else:
                return None
        else:
            log.error("Unknown type: " % type)
            exit(0)
