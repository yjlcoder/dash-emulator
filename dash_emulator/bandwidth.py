import time
from abc import ABC, abstractmethod
from typing import List

from dash_emulator.download import DownloadEventListener


class BandwidthUpdateListener(ABC):
    @abstractmethod
    async def on_bandwidth_update(self, bw: int) -> None:
        """
        Parameters
        ----------
        bw: int
            The latest bandwidth estimate in bps (bytes per second)
        """
        pass


class BandwidthMeter(ABC):
    @property
    @abstractmethod
    def bandwidth(self) -> int:
        """
        Returns
        -------
        bw: int
            The bandwidth estimate in bps (bytes per second)
        """
        pass


class BandwidthMeterImpl(BandwidthMeter, DownloadEventListener):
    def __init__(self, init_bandwidth: int, smooth_factor: float,
                 bandwidth_update_listeners: List[BandwidthUpdateListener]):
        """
        The formula to estimate the bandwidth is
            bandwidth = last_bandwidth * smooth_factor + latest_bandwidth * (1-smooth_factor)

        Parameters
        ----------
        init_bandwidth: int
            The initial bandwidth in bps (bytes per second)
        smooth_factor : float
            The smooth factor in use.
        bandwidth_update_listeners: List[BandwidthUpdateListener]
            A list of bandwidth update listeners
        """
        self._bw = init_bandwidth
        self.smooth_factor = smooth_factor
        self.listeners = bandwidth_update_listeners

        self.updated = False
        self.bytes_transferred = 0
        self.transmission_start_time = None
        self.transmission_end_time = None

    async def on_transfer_start(self, url) -> None:
        self.transmission_start_time = time.time()
        self.bytes_transferred = 0
        print("Transmission starts. URL: " + url)

    async def on_bytes_transferred(self, length: int, url: str, position: int, size: int) -> None:
        self.bytes_transferred += length

    async def on_transfer_end(self, size: int, url: str) -> None:
        self.transmission_end_time = time.time()
        self.update_bandwidth()
        self.bytes_transferred = 0

        for listener in self.listeners:
            await listener.on_bandwidth_update(self._bw)

    @property
    def bandwidth(self) -> int:
        return self._bw

    def update_bandwidth(self):
        if not self.updated:
            self._bw = 8 * self.bytes_transferred / (self.transmission_end_time - self.transmission_start_time)
        else:
            self._bw = self._bw * self.smooth_factor + \
                       (8 * self.bytes_transferred) / (self.transmission_end_time - self.transmission_start_time) * \
                       (1 - self.smooth_factor)
        self.updated = True
