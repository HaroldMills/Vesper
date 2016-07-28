"""Module containing class `AmplitudeAxis`."""


from vesper.signal.axis import Axis


'''
a.name                   # e.g. "Amplitude", "Power"
a.units                  # `Bunch` with `plural`, `singular`, and
                         # `abbreviation` attributes
'''


class AmplitudeAxis(Axis):
    
    
    def __init__(self, name='Amplitude', units=None):
        super().__init__(name, units)


    def __eq__(self, other):
        return isinstance(other, AmplitudeAxis) and Axis.__eq__(self, other)