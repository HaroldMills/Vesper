"""Utility functions pertaining to signals."""


def seconds_to_frames(seconds, frame_rate):
    return int(round(seconds * frame_rate))
