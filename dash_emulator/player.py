from abc import ABC, abstractmethod

from dash_emulator.models import State


class Player(ABC):
    @property
    @abstractmethod
    def state(self) -> State:
        """
        Get current state

        Returns
        -------
        state: State
            The current state
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start the playback
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the playback and reset everything
        """
        pass

    @abstractmethod
    def pause(self) -> None:
        """
        Pause the playback
        """
        pass


class DASHPlayer(Player):
    def __init__(self):
        self._state = State.IDLE

    @property
    def state(self) -> State:
        return self._state

    def start(self) -> None:
        pass

    def stop(self) -> None:
        raise NotImplementedError

    def pause(self) -> None:
        raise NotImplementedError
