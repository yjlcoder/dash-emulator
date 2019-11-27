from dash_emulator import monitor, config, mpd, logger

log = logger.getLogger(__name__)


class ABRController(object):
    def __init__(self, mpd_obj: mpd.MPD, speedMonitor: monitor.SpeedMonitor, cfg: config.Config):
        self.mpd = mpd_obj
        self.speedMonitor = speedMonitor
        self.cfg = cfg

    def choose(self, type) -> mpd.Representation:
        # TODO: change this
        if type == 'video':
            if len(self.mpd.videoAdaptationSet.representations) > 0:
                return self.mpd.videoAdaptationSet.representations[0]
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
