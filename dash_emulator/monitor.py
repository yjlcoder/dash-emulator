from dash_emulator import config, logger

log = logger.getLogger(__name__)


class SpeedMonitor(object):
    def __init__(self, cfg):
        self.cfg = cfg  # type: config.Config

        self.avg_bandwidth = 0
        self.last_speed = -1

    async def feed(self, data, time):
        if self.last_speed < 0:
            self.last_speed = data / time
            self.avg_bandwidth = self.last_speed
        else:
            self.last_speed = data / time
            self.avg_bandwidth = self.cfg.smoothing_factor * self.last_speed + (
                        1 - self.cfg.smoothing_factor) * self.avg_bandwidth

    def print(self):
        log.info("Avg bandwidth: %d bps" % (self.avg_bandwidth * 8))

    def get_speed(self):
        return self.avg_bandwidth
