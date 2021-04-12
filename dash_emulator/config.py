class Config(object):
    # Max initial bitrate (bps)
    max_initial_bitrate = 1000000

    # Min Duration for quality increase (ms)
    min_duration_for_quality_increase_ms = 6000

    # Max duration for quality decrease (ms)
    max_duration_for_quality_decrease_ms = 8000

    # Min duration to retrain after discard (ms)
    min_duration_to_retrain_after_discard_ms = 8000

    # Bandwidth fraction
    bandwidth_fraction = 0.75

    # averageSpeed = SMOOTHING_FACTOR * lastSpeed + (1-SMOOTHING_FACTOR) * averageSpeed;
    smoothing_factor = 0.5

    # minimum frame chunk size ratio
    # The size ratio of a segment which is for I-, P-, and B-frames.
    min_frame_chunk_ratio = 0.6

    # VQ threshold
    vq_threshold = 0.8

    # VQ threshold for size ratio
    vq_threshold_size_ratio = min_frame_chunk_ratio * (
            min_frame_chunk_ratio + (1 - min_frame_chunk_ratio) * vq_threshold)

    # Timeout max ratio
    timeout_max_ratio = 2

    # Update interval
    update_interval = 0.05

    # Chunk size
    chunk_size = 40960
