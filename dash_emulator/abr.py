from typing import Optional, Dict

from dash_emulator import logger, mpd, config, managers

log = logger.getLogger(__name__)


class ABRAlgorithm(object):
    def __init__(self):
        self.cfg = None

    def calculate_next_segment(self, current_speed: int, segment_index: int, representation_indices: Dict[str, int],
                               adaptation_sets: Dict[str, mpd.AdaptationSet], cfg: config.Config) -> Dict[str, int]:
        """
        :param cfg: configuration
        :param current_speed: Current estimated bandwidth (bps/s)
        :param representation_indices: A dictionary of current using representations. Keys are adaptation ids, and
               values are the representation index currently used in corresponding adaptation set.
        :param segment_index: The segment index to be calculated
        :param adaptation_sets: All available adaptation_sets to decide qualities
        :return: a new dictionary of next segments representations. Keys are adaptation ids, and values are the
               representation index will be used in corresponding adaptation set in next segment.
        """
        raise NotImplementedError


class NormalDashVideoABR(ABRAlgorithm):
    """
    This algorithm should only be used when there's only one video stream and only one or zero audio stream.
    """

    def determine_ideal_selected_index(self, effective_bw, adaptation_set: mpd.AdaptationSet):
        representations = adaptation_set.representations

        # representations are sorted from low bitrate to high bitrate. So scan from highest bitrate to lowest bitrate.
        for ind in reversed(range(0, len(representations))):
            representation = representations[ind]
            if representation.bandwidth < effective_bw:
                return ind

        # All representations require a higher bandwidth
        return 0  # lowest one

    def calculate_next_segment(self, current_bw: int, segment_index: int, representation_indices: Dict[str, int],
                               adaptation_sets: Dict[str, mpd.AdaptationSet], cfg: config.Config) -> Dict[str, str]:
        new_indices = representation_indices.copy()
        if segment_index == 0:
            current_bw = self.cfg.max_initial_bitrate
        left_bw = current_bw
        content_type_target = mpd.AdaptationSet.ContentType.VIDEO
        target_switch = {mpd.AdaptationSet.ContentType.VIDEO: mpd.AdaptationSet.ContentType.AUDIO,
                         mpd.AdaptationSet.ContentType.AUDIO: None}

        while content_type_target is not None:
            for adaptation_id, adaptation_set in adaptation_sets.items():
                effective_bw = left_bw * self.cfg.bandwidth_fraction
                if adaptation_set.content_type == content_type_target:
                    content_type_target = target_switch[content_type_target]
                    ideal_ind = self.determine_ideal_selected_index(effective_bw, adaptation_set)

                    if segment_index == 0:
                        return ideal_ind

                    current_representation = adaptation_set.representations[representation_indices[adaptation_id]]
                    ideal_representation = adaptation_set.representations[ideal_ind]

                    if ideal_representation.bandwidth > current_representation.bandwidth and managers.PlayManager().buffer_level < self.cfg.min_duration_for_quality_increase_ms:
                        new_indices[adaptation_id] = representation_indices[adaptation_id]
                    elif ideal_representation.bandwidth < current_representation.bandwidth and managers.PlayManager().buffer_level > self.cfg.max_duration_for_quality_decrease_ms:
                        new_indices[adaptation_id] = representation_indices[adaptation_id]
                    else:
                        new_indices[adaptation_id] = ideal_ind
                    left_bw = current_bw - adaptation_set.representations[new_indices[adaptation_id]].bandwidth
        return new_indices


class SRDDashVideoABR(ABRAlgorithm):

    def calculate_next_segment(self, current_speed: int, segment_index: int, representation_indices: Dict[str, int],
                               adaptation_sets: Dict[str, mpd.AdaptationSet], cfg: config.Config) -> Dict[str, int]:
        new_indices = representation_indices.copy()
        for key, value in new_indices.items():
            new_indices[key] = 2
        return new_indices


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
            self.cfg = None  # type: Optional[config.Config]
            self.abr = None  # type: Optional[ABRAlgorithm]

    def init(self, cfg: config.Config, abr_algorithm: ABRAlgorithm):
        self.cfg = cfg
        self.abr = abr_algorithm

    def calculate_next_segment(self, current_speed: int, segment_index, representation_indices: Dict[str, int],
                               adaptation_sets: Dict[str, mpd.AdaptationSet]) -> Dict[str, int]:
        return self.abr.calculate_next_segment(current_speed, segment_index, representation_indices, adaptation_sets,
                                               self.cfg)
