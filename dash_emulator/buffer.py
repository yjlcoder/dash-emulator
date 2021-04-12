from abc import ABC, abstractmethod


class BufferManager(ABC):
    @property
    @abstractmethod
    def buffer_level(self):
        """
        Returns
        -------
        buffer_level: float
            Current buffer level in seconds
        """
        pass

    @abstractmethod
    def enqueue_buffer(self, duration: float) -> None:
        """
        Enqueue some buffers into the buffer manager

        Parameters
        ----------
        duration: float
            The duration to enqueue
        """
        pass

    @abstractmethod
    def update_buffer(self, position: float) -> None:
        """
        Update the buffer level given the position

        Parameters
        ----------
        position: float
            The position of current playback in seconds
        """
        pass


class BufferManagerImpl(BufferManager):
    def __init__(self):
        self._buffer_position = 0
        self._position = 0

    def enqueue_buffer(self, duration: float) -> None:
        self._buffer_position += duration

    def update_buffer(self, position: float) -> None:
        self._position = position

    @property
    def buffer_level(self):
        return self._buffer_position - self._position
