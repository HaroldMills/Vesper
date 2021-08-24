"""
Module containing PNF 2018 baseline tseep and thrush detectors.

The baseline detectors are variants of the PNF energy detector that have
precision-recall curves that are very similar to those of variants of the
Old Bird Tseep and Thrush detectors that omit the post-processing steps
(including the clip merging and suppression steps) of those detectors.
"""


import numpy as np

from vesper.pnf.pnf_energy_detector_1_0 import (
    Detector, _FirFilter, _seconds_to_samples, _SeriesProcessor,
    _SeriesProcessorChain)
from vesper.util.bunch import Bunch


class BaselineDetector(Detector):
    
    """
    Baseline detector.
    
    The baseline detector is derived from the PNF energy detector, but
    replaces some computations (including for in-band power filtering and
    transient-finding) with ones that emulate those of the Old Bird
    detectors.
    """
    
    
    def _create_power_filter(self, input_sample_rate):
        
        filter_length = _seconds_to_samples(
            self.settings.integration_time, input_sample_rate)
        
        return _TimeIntegrator(
            'Time Integrator', filter_length, input_sample_rate)


    def _create_series_processors_aux(self):
        
        s = self.settings
        
        processors = [
            
            _TransientFinder(
                s.min_transient_duration, s.max_transient_duration),
            
            _Clipper(
                s.initial_clip_padding, s.clip_duration,
                self._input_sample_rate)
            
        ]
            
        return _SeriesProcessorChain(processors)
    
        
    def _get_threshold_crossings(self, ratios, threshold):
     
        x0 = ratios[:-1]
        x1 = ratios[1:]
         
        # Find indices where ratio rises above threshold.
        t = threshold
        rise_indices = np.where((x0 <= t) & (x1 > t))[0] + 1
         
        # Find indices where ratio falls below threshold inverse.
        t = 1 / t
        fall_indices = np.where((x0 >= t) & (x1 < t))[0] + 1
        
        # Convert indices to times.
        rise_times = self._convert_indices_to_times(rise_indices)
        fall_times = self._convert_indices_to_times(fall_indices)
        
        # Tag rises and falls with booleans, combine, and sort.
        return sorted(
            [(t, True) for t in rise_times] +
            [(t, False) for t in fall_times])
    

class _TimeIntegrator(_FirFilter):
     
    # An alternative to making this class an `_FirFilter` subclass would
    # be to use the `np.cumsum` function to compute the cumulative sum
    # of the input and then the difference between the result and a
    # delayed version of the result. That approach is more efficient
    # but it has numerical problems for sufficiently long inputs
    # (the cumulative sum of the squared samples grows ever larger, but
    # the samples do not, so you'll eventually start throwing away sample
    # bits), so I have chosen not to use it. An alternative would be to use
    # Cython or Numba or something like that to implement the integration
    # in a way that is both faster and accurate for arbitrarily long inputs.
     
    def __init__(self, name, integration_length, input_sample_rate):
        coefficients = np.ones(integration_length) / integration_length
        super().__init__(name, coefficients, input_sample_rate)
 

_STATE_DOWN = 0
_STATE_UP = 1
_STATE_HOLDING = 2


class _TransientFinder(_SeriesProcessor):
      
    """Finds transients in a series of threshold crossings."""
      
      
    def __init__(self, min_duration, max_duration):
          
        self._min_duration = min_duration
        self._max_duration = max_duration
          
        self._state = _STATE_DOWN
          
        self._start_time = 0
        """
        time of start of current transient.
          
        The value of this attribute only has meaning for the up and holding
        states. It does not mean anything for the down state.
        """
          
          
    def process(self, crossings):
           
        transients = []
        emit = transients.append
           
        for time, rise in crossings:
       
            if self._state == _STATE_DOWN:
       
                if rise:
                    # rise while down
       
                    # Start new transient.
                    self._start_time = time
                    self._state = _STATE_UP
       
                # Do nothing for fall while down.
       
            elif self._state == _STATE_UP:
       
                if rise:
                    # rise while up
       
                    if time == self._start_time + self._max_duration:
                        # rise right at end of maximal transient
                           
                        # Emit maximal transient.
                        emit((self._start_time, self._max_duration))
                           
                        # Return to down state. It seems a little odd that
                        # a rise would return us to the down state, but
                        # that is what happens in the original Old Bird
                        # detector (see line 252 of the original detector
                        # source code file splimflipflop.c), and we
                        # (somewhat arbitrarily) choose to emulate that
                        # here. This code should seldom execute on real
                        # inputs, since it should be rare for two
                        # consecutive rises to occur precisely
                        # `self._max_length` samples apart.
                        self._state = _STATE_DOWN
                           
                    elif time > self._start_time + self._max_duration:
                        # rise past end of maximal transient
       
                        # Emit maximal transient
                        emit((self._start_time, self._max_duration))
       
                        # Start new transient.
                        self._start_time = time
       
                    # Do nothing for rise before end of maximal transient.
       
                else:
                    # fall while up
       
                    if time < self._start_time + self._min_duration:
                        # fall before end of minimal transient
       
                        self._state = _STATE_HOLDING
       
                    else:
                        # fall at or after end of minimal transient
       
                        duration = time - self._start_time
       
                        # Truncate transient if after end of maximal transient.
                        if duration > self._max_duration:
                            duration = self._max_duration
       
                        # Emit transient.
                        emit((self._start_time, duration))
                           
                        self._state = _STATE_DOWN
       
            else:
                # holding after short transient
       
                if rise:
                    # rise while holding after short transient
       
                    if time > self._start_time + self._min_duration:
                        # rise follows end of minimal transient by at least
                        # one non-transient sample
                           
                        # Emit minimal transient.
                        emit((self._start_time, self._min_duration))
       
                        # Start new transient.
                        self._start_time = time
                           
                    self._state = _STATE_UP
       
                else:
                    # fall while holding after short transient
       
                    if time >= self._start_time + self._min_duration:
                        # fall at or after end of minimal transient
       
                        # Emit minimal transient.
                        emit((self._start_time, self._min_duration))
       
                        self._state = _STATE_DOWN
       
                    # Do nothing for fall before end of minimal transient.
   
        return transients
    
    
class _Clipper(_SeriesProcessor):
    
    
    def __init__(self, initial_padding, duration, sample_rate):
        self._initial_padding = initial_padding
        self._duration = duration
        self._sample_rate = sample_rate
        self._length = _seconds_to_samples(duration, sample_rate)
        
        
    def process(self, clips):
        return [self._get_bounds(clip) for clip in clips]
    
    
    # TODO: Should we do something special if the clip end index is past
    # the signal end index? We currently don't worry about this.
    def _get_bounds(self, clip):
        start_time, _ = clip
        start_time = max(start_time - self._initial_padding, 0)
        start_index = _seconds_to_samples(start_time, self._sample_rate)
        return (start_index, self._length)

    
_TSEEP_SETTINGS = Bunch(
    window_type='hann',
    window_size=.005,                 # seconds
    hop_size=50,                      # percent
    start_frequency=6000,             # hertz
    end_frequency=10000,              # hertz
    integration_time=.090,            # seconds
    delay=.020,                       # seconds
    thresholds=[2],                   # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.050,        # seconds
    clip_duration=.300                # seconds
)


_THRUSH_SETTINGS = Bunch(
    window_type='hann',
    window_size=.005,                 # seconds
    hop_size=50,                      # percent
    start_frequency=2800,             # hertz
    end_frequency=5000,               # hertz
    integration_time=.180,            # seconds
    delay=.020,                       # seconds
    thresholds=[1.3],                 # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.050,        # seconds
    clip_duration=.400                # seconds
)


class TseepDetector(BaselineDetector):
    
    
    extension_name = 'PNF 2018 Baseline Tseep Detector 1.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_TSEEP_SETTINGS, sample_rate, listener)


class ThrushDetector(BaselineDetector):
    
    
    extension_name = 'PNF 2018 Baseline Thrush Detector 1.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_THRUSH_SETTINGS, sample_rate, listener)
