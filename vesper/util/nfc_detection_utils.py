"""Utility functions pertaining to detection."""


import numpy as np

from vesper.util.bunch import Bunch
from vesper.util.spectrogram import Spectrogram
import vesper.util.data_windows as data_windows
import vesper.util.measurements as measurements


_WINDOW_TYPE_NAME = 'Hann'
_WINDOW_SIZE = 128
_WINDOW = data_windows.create_window(_WINDOW_TYPE_NAME, _WINDOW_SIZE)
_SPECTROGRAM_SETTINGS = Bunch(
    window=_WINDOW,
    hop_size=32,
    dft_size=128,
    reference_power=1)
_DETECTOR_CONFIG = Bunch(
    spectrogram_settings=_SPECTROGRAM_SETTINGS,
    start_freq=6000,
    end_freq=10000,
    typical_background_percentile=50,
    small_background_percentile=10,
    bit_threshold_factor=5,
    min_event_duration=.01,
    max_event_duration=.2,
    min_event_separation=.02,
    min_event_density=50)


def get_longest_selection(selections):
    if len(selections) == 0:
        return None
    else:
        lengths = np.array([_get_selection_duration(s) for s in selections])
        i = np.argmax(lengths)
        return selections[i]


def _get_selection_duration(selection):
    start_time, end_time = selection
    return end_time - start_time


def detect_tseeps(audio):
    return detect_events(audio, _DETECTOR_CONFIG)


def detect_events(audio, config):

    spectrogram = Spectrogram(audio, config.spectrogram_settings)

    x, times = measurements.apply_measurement_to_spectra(
        measurements.entropy, spectrogram,
        start_freq=config.start_freq, end_freq=config.end_freq,
        denoise=True, block_size=1)

    if len(times) < 2:
        return []

    else:
        # spectrogram has at least two frames

        period = times[1] - times[0]
        min_event_length = _to_frames(config.min_event_duration, period)
        max_event_length = _to_frames(config.max_event_duration, period)
        min_event_separation = _to_frames(config.min_event_separation, period)

        detector_config = Bunch(
            typical_background_percentile=config.typical_background_percentile,
            small_background_percentile=config.small_background_percentile,
            bit_threshold_factor=config.bit_threshold_factor,
            min_event_length=min_event_length,
            max_event_length=max_event_length,
            min_event_separation=min_event_separation,
            min_event_density=config.min_event_density)

        selections, _ = _detect(-x, detector_config)

        return [_convert_selection(s, times[0], period) for s in selections]


def _to_frames(duration, frame_period):
    num_frames = int(round(duration / frame_period))
    return num_frames if num_frames >= 1 else 1


def _convert_selection(selection, time_offset, frame_period):
    start_index, end_index = selection
    start_time = _to_seconds(start_index, time_offset, frame_period)
    end_time = _to_seconds(end_index - 1, time_offset, frame_period)
    return (start_time, end_time)


def _to_seconds(i, time_offset, frame_period):
    return time_offset + i * frame_period


def _detect(x, config):

    typical = np.percentile(x, config.typical_background_percentile)
    small = np.percentile(x, config.small_background_percentile)
    bit_threshold = typical + config.bit_threshold_factor * (typical - small)
    bits = np.zeros_like(x)
    bits[x >= bit_threshold] = 1

    selections = []
    parsing_event_candidate = False

    # These are just to keep Python code checkers like PyDev from
    # complaining that these variables may be undefined below.
    start_index = None
    zero_run_length = 0

    for i, bit in enumerate(bits):

        if parsing_event_candidate:

            if bit == 1:
                zero_run_length = 0

            else:

                zero_run_length += 1

                if zero_run_length == config.min_event_separation:
                    # event candidate ended

                    end_index = i - zero_run_length + 1
                    candidate_bits = bits[start_index:end_index]

                    if _is_event(candidate_bits, config):
                        selections.append((start_index, end_index))

                    parsing_event_candidate = False

        elif bit:
            # start of new event candidate

            parsing_event_candidate = True
            start_index = i
            zero_run_length = 0

    if parsing_event_candidate:
        # exited loop while parsing an event candidate

        end_index = i - zero_run_length + 1
        candidate_bits = bits[start_index:end_index]

        if _is_event(candidate_bits, config):
            selections.append((start_index, end_index))

    return (selections, bit_threshold)


def _is_event(bits, config):
    length = len(bits)
    density = 100 * np.sum(bits) / float(length)
    return length >= config.min_event_length and \
           length <= config.max_event_length and \
           density >= config.min_event_density
