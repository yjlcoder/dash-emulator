from abc import ABC, abstractmethod


class BytesDownloadedListener(ABC):
    @abstractmethod
    async def on_bytes_downloaded(self, length: int, url: str, position: int, size: int) -> None:
        """
        Parameters
        ----------
        length: int
            The length downloaded since last call, in bytes
        url: str
            The url of current download session
        position: int
            The current position of the stream, in bytes
        size: int
            The size of the content: in bytes
        """
        pass


class DownloadCompleteListener(ABC):
    @abstractmethod
    async def on_download_complete(self, size: int, url: str) -> None:
        """
        Parameters
        ----------
        size: int
            The size of the complete download
        url: str
            The url of the complete download
        """
        pass
