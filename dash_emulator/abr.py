from typing import Optional

from dash_emulator import monitor, config, mpd, logger, managers

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
            self.cfg = None  # type: Optional[config.Config]

    def init(self, mpd_obj: mpd.MPD, speed_monitor: monitor.SpeedMonitor, cfg: config.Config):
        self.mpd = mpd_obj
        self.speed_monitor = speed_monitor
        self.cfg = cfg

    def get_representation(self, ind, type):
        if type == 'video':
            return self.mpd.videoAdaptationSet.representations[ind]
        elif type == 'audio':
            return self.mpd.audioAdaptationSet.representations[ind]

    def choose(self, type) -> int:
        if type == 'video':
            current_ind = managers.PlayManager().current_video_representation_ind
            init_seg = (current_ind == -1)
            ideal_ind = self.determine_ideal_selected_index(type, init_seg)

            if init_seg:
                return ideal_ind

            current_representation = self.get_representation(current_ind, type)
            ideal_representation = self.get_representation(ideal_ind, type)

            if ideal_representation.bandwidth > current_representation.bandwidth and managers.PlayManager().buffer_level < self.cfg.min_duration_for_quality_increase_ms:
                selected_ind = current_ind
            elif ideal_representation.bandwidth < current_representation.bandwidth and managers.PlayManager().buffer_level > self.cfg.max_duration_for_quality_decrease_ms:
                selected_ind = current_ind
            else:
                selected_ind = ideal_ind
            return selected_ind

        elif type == 'audio':
            if len(self.mpd.videoAdaptationSet.representations) > 0:
                return self.mpd.audioAdaptationSet.representations[0]
            else:
                return None
        else:
            log.error("Unknown type: " % type)
            exit(0)

    def determine_ideal_selected_index(self, type, init_seg=False):
        bitrate_estimate = monitor.SpeedMonitor().get_speed()
        effective_bitrate = bitrate_estimate * self.cfg.bandwidth_fraction
        if init_seg:
            effective_bitrate = self.cfg.max_initial_bitrate

        if type == 'video':
            representations = self.mpd.videoAdaptationSet.representations

            # representations are sorted from low bitrate to high bitrate
            for ind in reversed(range(0, len(representations))):
                representation = representations[ind]
                if representation.bandwidth < effective_bitrate:
                    return ind

            # All representations require a higher bandwidth
            return 0  # lowest one
        else:
            # FIXME: Implement it
            log.error("The ABR algorithm doesn't support other types now.")
            exit(-1)
