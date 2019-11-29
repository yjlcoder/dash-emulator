class Config(object):
    def __init__(self, args):
        self.min_buffer = 6000
        self.max_buffer = 8000

        # averageSpeed = SMOOTHING_FACTOR * lastSpeed + (1-SMOOTHING_FACTOR) * averageSpeed;
        self.smoothing_factor = 0.5

        # minimum frame chunk size ratio
        # The size ratio of a segment which is for I-, P-, and B-frames.
        self.min_frame_chunk_ratio = 0.6

        # VQ threshold
        self.vq_threshold = 0.8

        # VQ threshold for size ratio
        self.vq_threshold_size_ratio = self.min_frame_chunk_ratio * (self.min_frame_chunk_ratio + (1-self.min_frame_chunk_ratio) * self.vq_threshold)

        # Timeout max ratio
        self.timeout_max_ratio = 2

        # Update interval
        self.update_interval = 0.05

        # Chunk size
        self.chunk_size = 40960
