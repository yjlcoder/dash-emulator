import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import aiohttp


class DownloadEventListener(ABC):
    @abstractmethod
    async def on_bytes_transferred(self, length: int, url: str, position: int, size: int) -> None:
        """
        Parameters
        ----------
        length: int
            The length transferred since last call, in bytes
        url: str
            The url of current request
        position: int
            The current position of the stream, in bytes
        size: int
            The size of the content: in bytes
        """
        pass

    @abstractmethod
    async def on_transfer_end(self, size: int, url: str) -> None:
        """
        Parameters
        ----------
        size: int
            The size of the complete transmission
        url: str
            The url of the complete transmission
        """
        pass

    @abstractmethod
    async def on_transfer_start(self, url) -> None:
        """
        Parameters
        ----------
        url: str
            The url of the transmission
        """


class DownloadManager(ABC):
    @property
    @abstractmethod
    def is_busy(self):
        """
        If a download session is running, return True. Return False otherwise.
        """
        pass

    @abstractmethod
    async def download(self, url, save=False) -> Optional[bytes]:
        """
        Start download

        Parameters
        ----------
        save
        url: str
            The URL of the source to download from
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Close the download session

        """
        pass

    async def stop(self):
        """
        Stop current request
        """
        pass


class DownloadManagerImpl(DownloadManager):
    log = logging.getLogger('DownloadManagerImpl')

    def __init__(self,
                 event_listeners: List[DownloadEventListener],
                 write_to_disk=False,
                 chunk_size=4096
                 ):
        """
        Parameters
        ----------
        event_listeners: List[DownloadEventListener],
            Listeners to events of some bytes downloaded
            
        write_to_disk: bool
            Should we write the downloaded bytes to the disk

        chunk_size: int
            How any bytes should be downloaded at once
        """
        self.event_listeners = event_listeners
        self.write_to_disk = write_to_disk
        self.chunk_size = chunk_size

        self._busy = False
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def is_busy(self) -> bool:
        return self._busy

    async def download(self, url, save=False) -> Optional[bytes]:
        self._busy = True
        self.log.info("Start downloading %s" % url)

        if self._session is None:
            self._session = aiohttp.ClientSession()

        content = bytearray()
        # TODO: support write to disk
        async with self._session.get(url) as resp:
            position = 0
            for listener in self.event_listeners:
                await listener.on_transfer_start(url)
            while True:
                chunk = await resp.content.read(self.chunk_size)
                if not chunk:
                    # Download complete, call listeners
                    for listener in self.event_listeners:
                        await listener.on_transfer_end(resp.content_length, url)
                    break
                size = len(chunk)
                if save:
                    content.extend(chunk)
                position += size
                for listener in self.event_listeners:
                    await listener.on_bytes_transferred(size, url, position, resp.content_length)
        self._busy = False
        return bytes(content) if save else None

    async def close(self) -> None:
        """
        You can still download things after you close the session, but it is not recommended.
        """
        if self._session is not None:
            await self._session.close()
