class Config(object):
    def __init__(self, args):
        # Max initial bitrate (bps)
        self.max_initial_bitrate = 1000000

        # Min Duration for quality increase (ms)
        self.min_duration_for_quality_increase_ms= 6000

        # Max duration for quality decrease (ms)
        self.max_duration_for_quality_decrease_ms= 8000

        # Min duration to retrain after discard (ms)
        self.min_duration_to_retrain_after_discard_ms = 8000

        # Bandwidth fraction
        self.bandwidth_fraction = 0.75

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
