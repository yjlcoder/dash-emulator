class Config(object):
    def __init__(self, args):
        self.min_buffer = 6000
        self.max_buffer = 6000

        # averageSpeed = SMOOTHING_FACTOR * lastSpeed + (1-SMOOTHING_FACTOR) * averageSpeed;
        self.smoothing_factor = 0.5
