"""
Utility functions that calculate sunrise and sunset times.

This module currently wraps functions of the `astral` module that
calculate sunrise and sunset times. In the future we may rely on a
different module, such as `ephem`, for such calculations.
"""


import astral


_astral = astral.Astral()


def get_sunrise_time(date, lat, lon):
    return _astral.sunrise_utc(date, lat, lon)


def get_sunset_time(date, lat, lon):
    return _astral.sunset_utc(date, lat, lon)
