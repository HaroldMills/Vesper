"""Utility functions pertaining to signals."""


def seconds_to_frames(duration, frame_rate):
    return int(round(duration * frame_rate))
