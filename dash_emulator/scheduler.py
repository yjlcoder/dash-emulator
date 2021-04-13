import asyncio
from abc import abstractmethod, ABC
from asyncio import Task
from typing import Optional, Dict, Set, List

from dash_emulator.abr import ABRController
from dash_emulator.bandwidth import BandwidthMeter
from dash_emulator.buffer import BufferManager
from dash_emulator.download import DownloadManager
from dash_emulator.models import AdaptationSet


class SchedulerEventHandler(ABC):
    @abstractmethod
    def on_segment_download_start(self, index, selections):
        pass

    @abstractmethod
    def on_segment_download_complete(self, index):
        pass


class Scheduler(ABC):
    @abstractmethod
    def start(self, adaptation_sets: Dict[int, AdaptationSet]):
        pass

    @abstractmethod
    def update(self, adaptation_sets: Dict[int, AdaptationSet]):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @property
    @abstractmethod
    def is_end(self):
        pass


class SchedulerImpl(Scheduler):
    def __init__(self,
                 max_buffer_duration: float,
                 update_interval: float,
                 download_manager: DownloadManager,
                 bandwidth_meter: BandwidthMeter,
                 buffer_manager: BufferManager,
                 abr_controller: ABRController,
                 listeners: List[SchedulerEventHandler]):
        """
        Parameters
        ----------
        max_buffer_duration
            The maximum buffer duration.
            When available buffer longer than this value, the scheduler won't start new segment transmissions.
        update_interval
            The interval between updates if there's no download sessions
        download_manager
            A download manager to download video payloads
        bandwidth_meter
            An instance of bandwidth meter to estimate the bandwidth.
        buffer_manager
            An instance to provide the buffer information.
        abr_controller
            ABR Controller to update the representation selections.
        listeners
            A list of SchedulerEventHandler
        """

        self.max_buffer_duration = max_buffer_duration
        self.update_interval = update_interval

        self.download_manager = download_manager
        self.bandwidth_meter = bandwidth_meter
        self.buffer_manager = buffer_manager
        self.abr_controller = abr_controller
        self.listeners = listeners

        self.adaptation_sets: Optional[Dict[int, AdaptationSet]] = None
        self.started = False

        self._task: Optional[Task] = None
        self._index = 0
        self._representation_initialized: Set[str] = set()

        self._end = False

    async def loop(self):
        while True:
            # Check buffer level
            if self.buffer_manager.buffer_level > self.max_buffer_duration:
                await asyncio.sleep(self.update_interval)
                continue

            # Download one segment from each adaptation set
            selections = self.abr_controller.update_selection(self.adaptation_sets)
            for listener in self.listeners:
                listener.on_segment_download_start(self._index, selections)
            duration = 0
            for adaptation_set_id, selection in selections.items():
                adaptation_set = self.adaptation_sets[adaptation_set_id]
                representation = adaptation_set.representations.get(selection)
                representation_str = "%d:%d" % (adaptation_set_id, representation.id)
                if representation_str not in self._representation_initialized:
                    await self.download_manager.download(representation.initialization)
                    self._representation_initialized.add(representation_str)
                try:
                    segment = representation.segments[self._index]
                except IndexError:
                    self._end = True
                    return
                await self.download_manager.download(segment.url)
                duration = segment.duration
            for listener in self.listeners:
                listener.on_segment_download_complete(self._index)
            self._index += 1
            self.buffer_manager.enqueue_buffer(duration)

    def start(self, adaptation_sets: Dict[int, AdaptationSet]):
        self.adaptation_sets = adaptation_sets
        self._task = asyncio.create_task(self.loop())

    def update(self, adaptation_sets: Dict[int, AdaptationSet]):
        self.adaptation_sets = adaptation_sets

    async def stop(self):
        await self.download_manager.close()
        if self._task is not None:
            self._task.cancel()

    @property
    def is_end(self):
        return self._end
