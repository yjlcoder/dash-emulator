import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional, List

from dash_emulator_quic.buffer import BufferManager
from dash_emulator_quic.models import State, MPD
from dash_emulator_quic.mpd import MPDProvider
from dash_emulator_quic.scheduler import Scheduler


class PlayerEventListener(ABC):
    @abstractmethod
    async def on_state_change(self, position: float, old_state: State, new_state: State):
        pass


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
    async def start(self, mpd_url) -> None:
        """
        Start the playback

        Parameters
        ----------
        mpd_url

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
    def __init__(self,
                 update_interval: float,
                 min_rebuffer_duration: float,
                 min_start_buffer_duration: float,
                 buffer_manager: BufferManager,
                 mpd_provider: MPDProvider,
                 scheduler: Scheduler,
                 listeners: List[PlayerEventListener]):
        """
        Parameters
        ----------
        update_interval
            The interval between each loop

        min_rebuffer_duration
            The buffer level needed to restore the playback from stalls
        min_start_buffer_duration
            The buffer level needed to start the playback
        mpd_provider
            An MPDProvider instance to provide MPD information
        scheduler
            The scheduler which controls the segment downloads
        buffer_manager
            The buffer manager
        listeners:
            A list of player event listeners
        """
        self.update_interval = update_interval

        self.min_start_buffer_duration = min_start_buffer_duration
        self.min_rebuffer_duration = min_rebuffer_duration

        self.buffer_manager = buffer_manager
        self.scheduler = scheduler
        self.mpd_provider = mpd_provider
        self.listeners = listeners

        # MPD related
        self._mpd_obj: Optional[MPD] = None

        # State related
        self._state = State.IDLE

        # Actions related
        self._main_loop_task = None

        # Playback related
        self._playback_started = False
        self._position = 0.0

    @property
    def state(self) -> State:
        return self._state

    async def _switch_state(self, old_state: State, new_state: State):
        for listener in self.listeners:
            await listener.on_state_change(self._position, old_state, new_state)

    async def start(self, mpd_url) -> None:
        # If the player doesn't have an MPD object, the player waits for it
        # Else the player doesn't wait for it
        if self._mpd_obj is None:
            await self.mpd_provider.start(mpd_url)
            self._mpd_obj = self.mpd_provider.mpd
        else:
            asyncio.create_task(self.mpd_provider.start(mpd_url))

        # Start the scheduler
        self._state = State.BUFFERING
        self.scheduler.start(adaptation_sets=self._mpd_obj.adaptation_sets)

        self._main_loop_task = await self.main_loop()

        await self.scheduler.stop()

    def stop(self) -> None:
        raise NotImplementedError

    def pause(self) -> None:
        raise NotImplementedError

    async def main_loop(self):
        """
        The main loop.
        This method coordinate works between different components.
        """
        timestamp = 0
        while True:
            now = time.time()
            interval = now - timestamp
            timestamp = now

            # Update MPD object
            self._mpd_obj = self.mpd_provider.mpd

            if self._state == State.READY:
                self._position += interval

            self.buffer_manager.update_buffer(self._position)
            buffer_level = self.buffer_manager.buffer_level

            if self._state == State.READY:
                if buffer_level <= 0:
                    if self.scheduler.is_end:
                        await self._switch_state(self._state, State.END)
                        self._state = State.END
                        return
                    else:
                        await self._switch_state(self._state, State.BUFFERING)
                        self._state = State.BUFFERING
            elif self._state == State.BUFFERING:
                if not self._playback_started:
                    if buffer_level > self.min_start_buffer_duration:
                        self._playback_started = True
                        await self._switch_state(self._state, State.READY)
                        self._state = State.READY
                else:
                    if buffer_level > self.min_rebuffer_duration:
                        await self._switch_state(self._state, State.READY)
                        self._state = State.READY

            await asyncio.sleep(min(buffer_level, self.update_interval) if buffer_level > 0 else self.update_interval)
