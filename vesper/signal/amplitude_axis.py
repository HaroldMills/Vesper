"""Module containing `AmplitudeAxis` class."""


from .axis import Axis


'''
a.name                   # e.g. "Amplitude", "Power"
a.units                  # `Bunch` with `plural`, `singular`, and
                         # `abbreviation` attributes
'''


class AmplitudeAxis(Axis):
    
    
    def __init__(self, name='Amplitude', units=None):
        super().__init__(name, units)
