"""Module containing PNF 2017 basic tseep and thrush detectors."""


# TODO: Modify detector interface to support any number of listeners.


import numpy as np
import scipy.signal as signal

# from vesper.pnf.ratio_file_writer import RatioFileWriter
from vesper.util.bunch import Bunch
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


# The default tseep and thrush detector settings that follow yield
# detectors that perform very similarly to the Old Bird Tseep and
# Thrush detectors.


_TSEEP_SETTINGS = Bunch(
    start_frequency=6000,             # hertz
    end_frequency=10000,              # hertz
    window_size=.005,                 # seconds
    hop_size=.0025,                   # seconds
    integration_time=.090,            # seconds
    delay=.020,                       # seconds
    thresholds=[2],                   # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.2,          # seconds
    clip_duration=.6                  # seconds
)


_THRUSH_SETTINGS = Bunch(
    start_frequency=2800,             # hertz
    end_frequency=5000,               # hertz
    window_size=.005,                 # seconds
    hop_size=.0025,                   # seconds
    integration_time=.180,            # seconds
    delay=.020,                       # seconds
    thresholds=[1.3],                 # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.2,          # seconds
    clip_duration=.6                  # seconds
)


class Detector:
    
    """
    PNF 2017 basic transient detector.

    An instance of this class operates on a single audio channel. It has a
    `detect` method that takes a NumPy array of samples. The method can be
    called repeatedly with consecutive sample arrays. The `complete_detection`
    method should be called after the final call to the `detect` method.
    During detection, each time the detector detects a clip it notifies
    a listener by invoking the listener's `process_clip` method. The
    `process_clip` method must accept three arguments, the start index and
    length of the detected clip, and the detection threshold of the
    detector.
    
    See the `_TSEEP_SETTINGS` and `_THRUSH_SETTINGS` objects above for
    tseep and thrush NFC detector settings. The `TseepDetector` and
    `ThrushDetector` classes of this module subclass the `Detector`
    class with fixed settings, namely `_TSEEP_SETTINGS` AND
    `_THRUSH_SETTINGS`, respectively.
    """
    
    
    def __init__(
            self, settings, input_sample_rate, listener,
            debugging_listener=None):
        
        self._settings = settings
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        self._debugging_listener = debugging_listener
        
        self._signal_processor = self._create_signal_processor()
        self._series_processors = self._create_series_processors()
        
        self._num_samples_processed = 0
        self._unprocessed_samples = np.array([], dtype='float')
        self._num_samples_generated = 0
        
#         self._ratio_file_writer = RatioFileWriter(
#             input_sample_rate, self._signal_processor.hop_size,
#             listener.detector_name)
        

    def _create_signal_processor(self):
        
        s = self.settings
        
        fs = self._input_sample_rate
        window_size = _seconds_to_samples(s.window_size, fs)
        hop_size = _seconds_to_samples(s.hop_size, fs)
        dft_size = tfa_utils.get_dft_size(window_size)
        spectrograph = _Spectrograph(
            'Spectrograph', window_size, hop_size, dft_size, fs)
        
        bin_size = spectrograph.bin_size
        start_bin_num = _get_bin_num(s.start_frequency, bin_size)
        end_bin_num = _get_bin_num(s.end_frequency, bin_size)
        frequency_integrator = _FrequencyIntegrator(
            'Frequency Integrator', start_bin_num, end_bin_num,
            spectrograph.output_sample_rate)
        
        fs = frequency_integrator.output_sample_rate
        integration_length = _seconds_to_samples(s.integration_time, fs)
        time_integrator = _TimeIntegrator(
            'Time Integrator', integration_length, fs)
        
        fs = time_integrator.output_sample_rate
        delay = _seconds_to_samples(s.delay, fs)
        divider = _Divider('Divider', delay, fs)
        
        processors = [
            spectrograph,
            frequency_integrator,
            time_integrator,
            divider
        ]
        
        return _SignalProcessorChain(
            'Detector', processors, self._input_sample_rate,
            self._debugging_listener)
        

    def _create_series_processors(self):
        return dict(
            (t, self._create_series_processors_aux())
            for t in self._settings.thresholds)
    
    
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
    
        
    @property
    def settings(self):
        return self._settings
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def listener(self):
        return self._transient_finder.listener
    
    
    def detect(self, samples):
        
        # TODO: Consider having each signal processor keep track of which
        # of its input samples it has processed, saving unprocessed samples
        # for future calls to the `process` function, and remove such
        # functionality from this class. This would reduce redundant
        # computation and simplify this class, but require more storage
        # (each processor would have to concatenate unprocessed samples
        # to new samples in its `detect` method) and complicate the
        # processor classes. A third alternative would be to move this
        # functionality from this class to the `_SignalProcessorChain`
        # class, but not to the other signal processor classes.
        
        # Concatenate unprocessed samples received in previous calls to
        # this method with new samples.
        samples = np.concatenate((self._unprocessed_samples, samples))
        
        # Run signal processors on samples.
        ratios = self._signal_processor.process(samples)
           
        # self._ratio_file_writer.write(samples, ratios)
          
        for threshold in self._settings.thresholds:
            crossings = self._get_threshold_crossings(ratios, threshold)
            clips = self._series_processors[threshold].process(crossings)
            self._notify_listener(clips, threshold)
            
        num_samples_generated = len(ratios)
        num_samples_processed = \
            num_samples_generated * self._signal_processor.hop_size
        self._num_samples_processed += num_samples_processed
        self._unprocessed_samples = samples[num_samples_processed:]
        self._num_samples_generated += num_samples_generated
            
            
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
    
    
    def _convert_indices_to_times(self, indices):
        input_fs = self._signal_processor.input_sample_rate
        output_fs = self._signal_processor.output_sample_rate
        offset = self._num_samples_processed / input_fs + \
            self._signal_processor.output_time_offset
        return indices / output_fs + offset
    
    
    def _notify_listener(self, clips, threshold):
        for start_index, length in clips:
            self._listener.process_clip(start_index, length, threshold)
            
            
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        for threshold, processor in self._series_processors.items():
            clips = processor.complete_processing([])
            self._notify_listener(clips, threshold)
        

def _seconds_to_samples(duration, sample_rate):
    return int(round(duration * sample_rate))


def _get_bin_num(frequency, bin_size):
    return int(round(frequency / bin_size))


class _SignalProcessor:
    
    
    def __init__(self, name, record_size, hop_size, input_sample_rate):
        self._name = name
        self._record_size = record_size
        self._hop_size = hop_size
        self._input_sample_rate = input_sample_rate
        
    
    @property
    def name(self):
        return self._name
    
    
    @property
    def record_size(self):
        return self._record_size
    
    
    @property
    def hop_size(self):
        return self._hop_size
    
    
    @property
    def input_sample_rate(self):
        return self._input_sample_rate
    
    
    @property
    def output_sample_rate(self):
        return self.input_sample_rate / self.hop_size
    
    
    @property
    def output_time_offset(self):
        return (self.record_size - 1) / 2 / self.input_sample_rate
    
    
    def get_required_num_inputs(self, num_outputs):
        if num_outputs == 0:
            return 0
        else:
            return self.record_size + (num_outputs - 1) * self.hop_size
    
    
    def process(self, x):
        raise NotImplementedError()
    
        
class _Spectrograph(_SignalProcessor):
    
    
    def __init__(
            self, name, window_size, hop_size, dft_size, input_sample_rate):
        
        super().__init__(name, window_size, hop_size, input_sample_rate)
        
        self.window = HannWindow(window_size).samples
        self.dft_size = dft_size
        
        
    @property
    def bin_size(self):
        return self.input_sample_rate / self.dft_size
    
    
    def process(self, x):
        return tfa_utils.compute_spectrogram(
            x, self.window, self.hop_size, self.dft_size)


class _FrequencyIntegrator(_SignalProcessor):
    
    
    def __init__(self, name, start_bin_num, end_bin_num, input_sample_rate):
        super().__init__(name, 1, 1, input_sample_rate)
        self.start_bin_num = start_bin_num
        self.end_bin_num = end_bin_num
        
        
    def process(self, x):
        return x[:, self.start_bin_num:self.end_bin_num].sum(axis=1)

        
class _FirFilter(_SignalProcessor):
     
     
    def __init__(self, name, coefficients, input_sample_rate):
        super().__init__(name, len(coefficients), 1, input_sample_rate)
        self.coefficients = coefficients
         
         
    def process(self, x):
        return signal.fftconvolve(x, self.coefficients, mode='valid')
     
     
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
 
 
class _Divider(_SignalProcessor):
     
     
    def __init__(self, name, delay, input_sample_rate):
        super().__init__(name, delay + 1, 1, input_sample_rate)
        self.delay = delay
         
         
    def process(self, x):
        
        # Avoid potential divide-by-zero issues by replacing zero values
        # with very small ones.
        x[np.where(x == 0)] = 1e-20
         
        return x[self.delay:] / x[:-self.delay]
             
    
class _SignalProcessorChain(_SignalProcessor):
    
    
    @staticmethod
    def _get_record_size(processors):
        record_size = processors[-1].record_size
        for p in reversed(processors[:-1]):
            record_size = p.get_required_num_inputs(record_size)
        return record_size
    
    
    @staticmethod
    def _get_hop_size(processors):
        hop_size = 1
        for p in processors:
            hop_size *= p.hop_size
        return hop_size
        
        
    def __init__(
            self, name, processors, input_sample_rate,
            debugging_listener=None):
        
        record_size = _SignalProcessorChain._get_record_size(processors)
        hop_size = _SignalProcessorChain._get_hop_size(processors)
        super().__init__(name, record_size, hop_size, input_sample_rate)
        self._processors = processors
        self._debugging_listener = debugging_listener
        
        
    def process(self, x):
        for processor in self._processors:
            x = processor.process(x)
            if self._debugging_listener is not None:
                self._debugging_listener.handle_samples(
                    processor.name, x, processor.output_sample_rate)
        return x
    
    
class _SeriesProcessor:
    
    
    def process(self, items):
        raise NotImplementedError()
    
    
    def complete_processing(self, items):
        return self.process(items)
    
    
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

    
class _SeriesProcessorChain(_SeriesProcessor):
    
    
    def __init__(self, processors):
        self._processors = processors
        
        
    def process(self, items):
        for processor in self._processors:
            items = processor.process(items)
        return items
    
    
    def complete_processing(self, items):
        for processor in self._processors:
            items = processor.complete_processing(items)
        return items
    
    
class TseepDetector(Detector):
    
    
    extension_name = 'PNF 2017 Basic Tseep Detector 1.0-alpha.1'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_TSEEP_SETTINGS, sample_rate, listener)

    
class ThrushDetector(Detector):
    
    
    extension_name = 'PNF 2017 Basic Thrush Detector 1.0-alpha.1'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_THRUSH_SETTINGS, sample_rate, listener)
