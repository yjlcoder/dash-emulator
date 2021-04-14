from dash_emulator.abr import DashABRController
from dash_emulator.bandwidth import BandwidthMeterImpl
from dash_emulator.buffer import BufferManagerImpl
from dash_emulator.config import Config
from dash_emulator.download import DownloadManagerImpl
from dash_emulator.event_logger import EventLogger
from dash_emulator.mpd.parser import DefaultMPDParser
from dash_emulator.mpd.providers import MPDProviderImpl
from dash_emulator.player import Player, DASHPlayer
from dash_emulator.scheduler import SchedulerImpl


def build_dash_player() -> Player:
    """
    Build a MPEG-DASH Player

    Returns
    -------
    player: Player
        A MPEG-DASH Player
    """
    cfg = Config
    buffer_manager = BufferManagerImpl()
    event_logger = EventLogger()
    mpd_provider = MPDProviderImpl(DefaultMPDParser(), cfg.update_interval, DownloadManagerImpl([]))
    bandwidth_meter = BandwidthMeterImpl(cfg.max_initial_bitrate, cfg.smoothing_factor, [])
    download_manager = DownloadManagerImpl([bandwidth_meter])
    abr_controller = DashABRController(2, 4, bandwidth_meter, buffer_manager)
    scheduler = SchedulerImpl(5, cfg.update_interval, download_manager, bandwidth_meter, buffer_manager,
                              abr_controller, [event_logger])
    return DASHPlayer(cfg.update_interval, min_rebuffer_duration=1, min_start_buffer_duration=2,
                      buffer_manager=buffer_manager, mpd_provider=mpd_provider, scheduler=scheduler)
