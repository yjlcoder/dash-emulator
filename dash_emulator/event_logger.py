import logging

from dash_emulator_quic.models import State
from dash_emulator_quic.player import PlayerEventListener
from dash_emulator_quic.scheduler import SchedulerEventListener


class EventLogger(SchedulerEventListener, PlayerEventListener):
    log = logging.getLogger("EventLogger")

    async def on_state_change(self, position: float, old_state: State, new_state: State):
        self.log.info("Switch state. pos: %.3f, from %s to %s" % (position, old_state, new_state))

    async def on_segment_download_start(self, index, selections):
        self.log.info("Download start. Index: %d, Selections: %s" % (index, str(selections)))

    async def on_segment_download_complete(self, index):
        self.log.info("Download complete. Index: %d" % index)
