"""Band-limited energy detector for Northern Goshawk (NOGO) sounds."""


from vesper.pnf.pnf_energy_detector_1_0 import Detector as PnfDetector
from vesper.util.bunch import Bunch


_DETECTOR_SETTINGS = Bunch(
    window_type='hann',
    window_size=.020,                           # seconds
    hop_size=50,                                # percent
    start_frequency=1000,                       # hertz
    end_frequency=3000,                         # hertz
    power_filter_passband_end_frequency=5,      # hertz
    power_filter_stopband_start_frequency=15,   # hertz
    power_filter_length=31,                     # samples
    delay=.100,                                 # seconds
    thresholds=[2.5],                           # dimensionless
    initial_clip_padding=.100,                  # seconds
    clip_duration=.600                          # seconds
)


class Detector(PnfDetector):
    
    extension_name = 'PSW NOGO Detector 0.0'
    
    def __init__(self, sample_rate, listener):
        super().__init__(_DETECTOR_SETTINGS, sample_rate, listener)
