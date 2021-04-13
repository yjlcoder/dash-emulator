from abc import ABC, abstractmethod
from typing import Dict, Optional

from dash_emulator.bandwidth import BandwidthMeter
from dash_emulator.buffer import BufferManager
from dash_emulator.models import AdaptationSet


class ABRController(ABC):
    @abstractmethod
    def update_selection(self, adaptation_sets: Dict[int, AdaptationSet]) -> Dict[int, int]:
        """
        Update the representation selections

        Parameters
        ----------
        adaptation_sets: Dict[int, AdaptationSet]
            The adaptation sets information

        Returns
        -------
        selection: Dict[int, int]
            A dictionary where the key is the index of an adaptation set, and
            the value is the chosen representation id for that adaptation set.
        """
        pass


class DashABRController(ABRController):
    def __init__(self,
                 panic_buffer: float,
                 safe_buffer: float,
                 bandwidth_meter: BandwidthMeter,
                 buffer_manager: BufferManager):
        """
        Parameters
        ----------
        panic_buffer: float
            The bitrate chosen won't go up when the buffer level is lower than panic buffer level
        safe_buffer: float
            The bitrate chosen won't go down when the buffer level is higher than safe buffer level
        bandwidth_meter: BandwidthMeter
            A bandwidth meter which could provide the latest bandwidth estimate
        buffer_manager : BufferManager
            A buffer manager which could provide the buffer level estimate
        """
        self.panic_buffer = panic_buffer
        self.safe_buffer = safe_buffer
        self.bandwidth_meter = bandwidth_meter
        self.buffer_manager = buffer_manager

        self._last_selections: Optional[Dict[int, int]] = None

    @staticmethod
    def choose_ideal_selection(adaptation_set, bw) -> int:
        representations = sorted(adaptation_set.representations.values(), key=lambda x: x.bandwidth, reverse=True)
        for representation in representations:
            if representation.bandwidth < bw:
                return representation.id

    def update_selection(self, adaptation_sets: Dict[int, AdaptationSet]) -> Dict[int, int]:
        # Only use 70% of measured bandwidth
        available_bandwidth = int(self.bandwidth_meter.bandwidth * 0.7)

        # Count the number of video adaptation sets and audio adaptation sets
        num_videos = 0
        num_audios = 0
        for adaptation_set in adaptation_sets.values():
            if adaptation_set.content_type == "video":
                num_videos += 1
            else:
                num_audios += 1

        # Calculate ideal selections
        if num_videos == 0 or num_audios == 0:
            bw_per_adaptation_set = available_bandwidth / (num_videos + num_audios)
            ideal_selection: Dict[int, int] = dict()
            for adaptation_set in adaptation_sets.values():
                ideal_selection[adaptation_set.id] = self.choose_ideal_selection(adaptation_set, bw_per_adaptation_set)
        else:
            bw_per_video = (available_bandwidth * 0.8) / num_videos
            bw_per_audio = (available_bandwidth * 0.2) / num_audios
            ideal_selection: Dict[int, int] = dict()
            for adaptation_set in adaptation_sets.values():
                if adaptation_set.content_type == "video":
                    ideal_selection[adaptation_set.id] = self.choose_ideal_selection(adaptation_set, bw_per_video)
                else:
                    ideal_selection[adaptation_set.id] = self.choose_ideal_selection(adaptation_set, bw_per_audio)

        buffer_level = self.buffer_manager.buffer_level
        final_selections = dict()

        # Take the buffer level into considerations
        if self._last_selections is not None:
            for id_, adaptation_set in adaptation_sets.items():
                representations = adaptation_set.representations
                last_repr = representations[self._last_selections.get(id_)]
                ideal_repr = representations[ideal_selection.get(id_)]
                if buffer_level < self.panic_buffer:
                    final_repr_id = last_repr.id if last_repr.bandwidth < ideal_repr.bandwidth else ideal_repr.id
                elif buffer_level > self.safe_buffer:
                    final_repr_id = last_repr.id if last_repr.bandwidth > ideal_repr.bandwidth else ideal_repr.id
                else:
                    final_repr_id = ideal_repr.id
                final_selections[id_] = final_repr_id
        else:
            final_selections = ideal_selection
        self._last_selections = final_selections
        return final_selections
