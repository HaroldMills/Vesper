# Utility functions concerning time intervals defined in terms of clip bounds.


from vesper.util.bunch import Bunch
import vesper.util.signal_utils as signal_utils


_CLIP_ALIGNMENTS = frozenset(['Center', 'Left', 'Right'])


def parse_clip_time_interval_preset(preset):

    if 'duration' in preset:
        # duration explicit

        duration = preset['duration']

        if duration <= 0:
            raise ValueError(f'Interval duration must be positive.')

        alignment = preset.get('alignment', 'Center')

        if alignment not in _CLIP_ALIGNMENTS:
            raise ValueError(
                f'Unrecognized clip alignment "{alignment}". '
                f'Alignment must be "Center", "Left", or "Right". ')

        offset = preset.get('offset', 0)

        result = Bunch(
            duration=duration,
            alignment=alignment,
            offset=offset)

    else:
        # duration implicit

        left_padding = preset.get('left_padding', 0)
        right_padding = preset.get('right_padding', 0)
        offset = preset.get('offset', 0)

        result = Bunch(
            left_padding=left_padding,
            right_padding=right_padding,
            offset=offset)

    return result


def get_clip_time_interval(clip, interval):

    def s2f(duration):
        return signal_utils.seconds_to_frames(duration, clip.sample_rate)

    if hasattr(interval, 'duration'):
        # duration explicit

        length = s2f(interval.duration)

        alignment = interval.alignment

        if alignment == 'Center':
            start_offset = (clip.length - length) // 2

        elif alignment == 'Left':
            start_offset = 0

        else:
            start_offset = clip.length - length

        start_offset -= s2f(interval.offset)

    else:
        # duration implicit

        offset = s2f(interval.offset)
        left_padding = s2f(interval.left_padding) + offset
        right_padding = s2f(interval.right_padding) - offset

        start_offset = -left_padding
        length = clip.length + left_padding + right_padding

    length = max(length, 0)

    return start_offset, length
