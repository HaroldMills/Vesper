from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
import vesper.util.clip_time_interval_utils as clip_time_interval_utils


# alignment shorthands
C = 'Center'
L = 'Left'
R = 'Right'


class ClipTimedIntervalUtilsTests(TestCase):


    def test_parse_clip_time_interval_spec(self):

        cases = [

            (ed(1), eb(1, C, 0)),
            (ed(1, C), eb(1, C, 0)),
            (ed(1, offset=.5), eb(1, C, .5)),
            (ed(1, offset=-.5), eb(1, C, -.5)),
            (ed(1, R, .5), eb(1, R, .5)),

            (id(), ib(0, 0, 0)),
            (id(1), ib(1, 0, 0)),
            (id(-1), ib(-1, 0, 0)),
            (id(right_padding=1), ib(0, 1, 0)),
            (id(right_padding=-1), ib(0, -1, 0)),
            (id(offset=1), ib(0, 0, 1)),
            (id(offset=-1), ib(0, 0, -1)),
            (id(1, 2), ib(1, 2, 0)),
            (id(1, offset=2), ib(1, 0, 2)),
            (id(None, 1, 2), ib(0, 1, 2)),
            (id(1, 2, 3), ib(1, 2, 3)),

        ]

        parse = clip_time_interval_utils.parse_clip_time_interval_spec
        for spec, expected in cases:
            actual = parse(spec)
            self.assertEqual(actual, expected)

    
    def test_parse_clip_time_interval_spec_errors(self):

        cases = [
            ed(0),
            ed(-1),
            ed(1, 'X')
        ]

        parse = clip_time_interval_utils.parse_clip_time_interval_spec
        for spec in cases:
            self.assert_raises(ValueError, parse, spec)


    def test_get_clip_time_interval(self):

        get = clip_time_interval_utils.get_clip_time_interval

        cases = [

            (eb(1, C, 0), (-2, 8)),
            (eb(1, L, 0), (0, 8)),
            (eb(1, R, 0), (-4, 8)),
            (eb(1, C, .25), (-4, 8)),
            (eb(1, C, -.25), (0, 8)),
            (eb(1, L, .25), (-2, 8)),
            (eb(1, R, -.25), (-2, 8)),
            (eb(2, C, 0), (-6, 16)),

            (ib(1, 0, 0), (-8, 12)),
            (ib(0, 1, 0), (0, 12)),
            (ib(0, 0, .25), (-2, 4)),
            (ib(1, 2, .5), (-12, 28)),

        ]

        get_interval = clip_time_interval_utils.get_clip_time_interval
        clip = Bunch(sample_rate=8, length=4)
        for spec, expected in cases:
            actual = get_interval(clip, spec)
            self.assertEqual(actual, expected)


def ed(duration, alignment=None, offset=None):

    """Constructs an explicit-duration spec dictionary."""

    result = {}

    if duration is not None:
        result['duration'] = duration

    if alignment is not None:
        result['alignment'] = alignment

    if offset is not None:
        result['offset'] = offset

    return result


def id(left_padding=None, right_padding=None, offset=None):

    """Constructs an implicit-duration spec dictionary."""

    result = {}

    if left_padding is not None:
        result['left_padding'] = left_padding

    if right_padding is not None:
        result['right_padding'] = right_padding

    if offset is not None:
        result['offset'] = offset

    return result


def eb(duration, alignment, offset):

    """Constructs an explicit-duration spec bunch."""

    return Bunch(
        duration=duration,
        alignment=alignment,
        offset=offset)


def ib(left_padding, right_padding, offset):

    """Constructs an implicit-duration spec bunch."""

    return Bunch(
        left_padding=left_padding,
        right_padding=right_padding,
        offset=offset)
