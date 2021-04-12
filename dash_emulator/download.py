import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import aiohttp

from dash_emulator.listeners import BytesDownloadedListener, DownloadCompleteListener


class DownloadManager(ABC):
    @property
    @abstractmethod
    def is_busy(self):
        """
        If a download session is running, return True. Return False otherwise.
        """
        pass

    @abstractmethod
    async def download(self, url):
        """
        Start download

        Parameters
        ----------
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
    log = logging.getLogger('DOwnloadManagerImpl')

    def __init__(self,
                 bytes_downloaded_listeners: List[BytesDownloadedListener],
                 complete_listeners: List[DownloadCompleteListener],
                 write_to_disk=False,
                 chunk_size=4096
                 ):
        """
        Parameters
        ----------
        bytes_downloaded_listeners: List[BytesDownloadedListener],
            Listeners to events of some bytes downloaded

        complete_listeners: List[DownloadCompleteListener],
            Listeners to events of the request got completely downloaded

        write_to_disk: bool
            Should we write the downloaded bytes to the disk

        chunk_size: int
            How any bytes should be downloaded at once
        """
        self.bytes_downloaded_listeners = bytes_downloaded_listeners
        self.complete_listeners = complete_listeners
        self.write_to_disk = write_to_disk
        self.chunk_size = chunk_size

        self._busy = False
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def is_busy(self) -> bool:
        return self._busy

    async def download(self, url):
        self._busy = True
        self.log.info("Start downloading %s" % url)

        if self._session is None:
            self._session = aiohttp.ClientSession()
        # TODO: support write to disk
        async with self._session.get(url) as resp:
            position = 0
            while True:
                chunk = await resp.content.read(self.chunk_size)
                if not chunk:
                    # Download complete, call listeners
                    for listener in self.complete_listeners:
                        await listener.on_download_complete(resp.content_length, url)
                    break
                size = len(chunk)
                position += size
                for listener in self.bytes_downloaded_listeners:
                    await listener.on_bytes_downloaded(size, url, position, resp.content_length)
        self._busy = False

    async def close(self):
        if self._session is not None:
            await self._session.close()
