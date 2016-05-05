"""Units constants for axis class unit tests."""


from vesper.util.bunch import Bunch


DEFAULT_UNITS = Bunch(plural=None, singular=None, abbreviation=None)
TIME_UNITS = Bunch(plural='seconds', singular='second', abbreviation='S')
FREQ_UNITS = Bunch(plural='hertz', singular='hertz', abbreviation='Hz')
POWER_UNITS = Bunch(plural='decibels', singular='decibel', abbreviation='dB')
