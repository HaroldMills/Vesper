from numbers import Number
import datetime

import numpy as np

from ..amplitude_axis import AmplitudeAxis
from ..axis import Axis
from ..index_axis import IndexAxis
from ..linear_mapping import LinearMapping
from ..sample_array_axis import SampleArrayAxis
from ..time_axis import TimeAxis
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch


_DEFAULT_UNITS = Bunch(plural=None, singular=None, abbreviation=None)
_TIME_UNITS = Bunch(plural='seconds', singular='second', abbreviation='S')
_FREQ_UNITS = Bunch(plural='hertz', singular='hertz', abbreviation='Hz')
_POWER_UNITS = Bunch(plural='decibels', singular='decibel', abbreviation='dB')


class AxisTests(TestCase):


    def test_init(self):
        pass
    