"""Module containing PNF 2017 basic tseep and thrush detectors."""


import numpy as np
import scipy.linalg as linalg
import scipy.signal as signal

from vesper.util.bunch import Bunch


_TSEEP_SETTINGS = Bunch(
    filter_f0=6000,                   # hertz
    filter_f1=10000,                  # hertz
    filter_bw=100,                    # hertz
    filter_duration=.00454,           # seconds, 100 samples at fs = 22050
    integration_time=.09070,          # seconds, 2000 samples at fs = 22050
    delay=.02,                        # seconds
    threshold=2,                      # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.15,         # seconds
    clip_duration=.5                  # seconds
)


_THRUSH_SETTINGS = Bunch(
    filter_f0=2800,                   # hertz
    filter_f1=5000,                   # hertz
    filter_bw=100,                    # hertz
    filter_duration=.00454,           # seconds, 100 samples at fs = 22050
    integration_time=.1814,           # seconds, 4000 samples at fs = 22050
    delay=.02,                        # seconds
    threshold=1.3,                    # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.15,         # seconds
    clip_duration=.6                  # seconds
)


class _Detector:
    
    """
    PNF 2017 basic transient detector.

    An instance of this class operates on a single audio channel. It has a
    `detect` method that takes a NumPy array of samples. The method can be
    called repeatedly with consecutive sample arrays. The `complete_detection`
    method should be called after the final call to the `detect` method.
    During detection, each time the detector detects a clip it notifies
    a listener by invoking the listener's `process_clip` method. The
    `process_clip` method must accept two arguments, the start index and
    length of the detected clip.
    
    See the `_TSEEP_SETTINGS` and `_THRUSH_SETTINGS` objects above for
    tseep and thrush NFC detector settings. The `TseepDetector` and
    `ThrushDetector` classes of this module subclass the `_Detector`
    class with fixed settings, namely `_TSEEP_SETTINGS` AND
    `_THRUSH_SETTINGS`, respectively.
    """
    
    
    def __init__(self, settings, sample_rate, listener):
        
        self._settings = settings
        self._sample_rate = sample_rate
        self._listener = listener
        
        self._signal_processor = self._create_signal_processor()
        self._series_processor = self._create_series_processor()
        
        self._num_samples_processed = 0
        self._recent_samples = np.array([], dtype='float')
        self._initial_samples_repeated = False
        

    def _create_signal_processor(self):
        
        coefficients = self._design_filter()
        
        s = self.settings
        
        integration_length = \
            _seconds_to_samples(s.integration_time, self.sample_rate)
        delay = _seconds_to_samples(s.delay, self.sample_rate)
        
        processors = [
            _FirFilter(coefficients),
            _Squarer(),
            _Integrator(integration_length),
            _Divider(delay),
        ]
        
        return _SignalProcessorChain(processors)
        
        
    def _design_filter(self):
        
        s = self.settings
        
        # We use a filter length that is proportional to the sample rate.
        # This yields filters with very similar frequency responses at
        # different sample rates.
        filter_length = \
            _seconds_to_samples(s.filter_duration, self.sample_rate)
        
        f0 = s.filter_f0
        f1 = s.filter_f1
        bw = s.filter_bw
        fs2 = self.sample_rate / 2
        bands = np.array([0, f0 - bw, f0, f1, f1 + bw, fs2]) / fs2
        
        desired = np.array([0, 0, 1, 1, 0, 0])
        
        return _firls(filter_length, bands, desired)
    
    
    def _create_series_processor(self):
        
        s = self.settings
        sample_rate = self.sample_rate
        
        min_transient_length = \
            _seconds_to_samples(s.min_transient_duration, sample_rate)
        max_transient_length = \
            _seconds_to_samples(s.max_transient_duration, sample_rate)
        
        initial_clip_padding = \
            _seconds_to_samples(s.initial_clip_padding, sample_rate)
        clip_length = _seconds_to_samples(s.clip_duration, sample_rate)
        
        processors = [
            _TransientFinder(min_transient_length, max_transient_length),
            _ClipBoundsSetter(initial_clip_padding, clip_length)
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
        
        augmented_samples = np.concatenate((self._recent_samples, samples))
        
        if len(augmented_samples) <= self._signal_processor.latency:
            # don't yet have enough samples to fill processing pipeline
            
            self._recent_samples = augmented_samples
            
        else:
            # have enough samples to fill processing pipeline
            
            # Run signal processors on samples.
            ratios = self._signal_processor.process(augmented_samples)
            
            # Get transient index offset.
            offset = self._num_samples_processed
            if not self._initial_samples_repeated:
                offset += self._signal_processor.latency
                self._initial_samples_repeated = True
                
            crossings = self._get_threshold_crossings(ratios, offset)
            
            clips = self._series_processor.process(crossings)
            
            self._notify_listener(clips)
            
            # Save trailing samples for next call to this method.
            self._recent_samples = \
                augmented_samples[-self._signal_processor.latency:]
            
        self._num_samples_processed += len(samples)
            
            
    def _get_threshold_crossings(self, ratios, offset):
    
        # Add one to index offset to compensate for processing latency
        # of this method.
        offset += 1
        
        x0 = ratios[:-1]
        x1 = ratios[1:]
        
        # Find indices where ratio rises above threshold.
        t = self.settings.threshold
        rise_indices = np.where((x0 <= t) & (x1 > t))[0] + offset
        
        # Find indices where ratio falls below threshold inverse.
        t = 1 / t
        fall_indices = np.where((x0 >= t) & (x1 < t))[0] + offset

        # Tag rises and falls with booleans, combine, and sort.
        return sorted(
            [(i, True) for i in rise_indices] +
            [(i, False) for i in fall_indices])
    
    
    def _notify_listener(self, clips):
        for start_index, length in clips:
            self._listener.process_clip(start_index, length)
            
            
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        # Send a final falling crossing to the series processor to
        # terminate a transient that may have started more than the
        # minimum clip duration before the end of the input but for
        # which for whatever reason there has not yet been a fall.
        fall = (self._num_samples_processed, False)
        clips = self._series_processor.complete_processing([fall])
        self._notify_listener(clips)
        

def _seconds_to_samples(duration, sample_rate):
    return int(round(duration * sample_rate))


class _SignalProcessor:
    
    
    def __init__(self, latency):
        self._latency = latency
        
        
    @property
    def latency(self):
        return self._latency
    
    
    def process(self, x):
        raise NotImplementedError()
    
    
class _FirFilter(_SignalProcessor):
    
    
    def __init__(self, coefficients):
        super().__init__(len(coefficients) - 1)
        self._coefficients = coefficients
        
        
    def process(self, x):
        return signal.fftconvolve(x, self._coefficients, mode='valid')
    
    
class _Squarer(_SignalProcessor):
    
    
    def __init__(self):
        super().__init__(0)
    
    
    def process(self, x):
        return x * x
    
    
class _Integrator(_FirFilter):
    
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
    
    def __init__(self, integration_length):
        coefficients = np.ones(integration_length) / integration_length
        super().__init__(coefficients)


class _Divider(_SignalProcessor):
    
    
    def __init__(self, delay):
        super().__init__(delay - 1)
        self._delay = delay
        
        
    def process(self, x):
        
        # Avoid potential divide-by-zero issues by replacing zero values
        # with very small ones.
        x[np.where(x == 0)] = 1e-20
        
        return x[self._delay:] / x[:-self._delay]
             
    
class _SignalProcessorChain(_SignalProcessor):
    
    
    def __init__(self, processors):
        latency = sum([p.latency for p in processors])
        super().__init__(latency)
        self._processors = processors
        
        
    def process(self, x):
        for processor in self._processors:
            x = processor.process(x)
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
    
    
    def __init__(self, min_length, max_length):
        
        self._min_length = min_length
        self._max_length = max_length
        
        self._state = _STATE_DOWN
        
        self._start_index = 0
        """
        index of start of current transient.
        
        The value of this attribute only has meaning for the up and holding
        states. It does not mean anything for the down state.
        """
        
        
    def process(self, crossings):
        
        transients = []
        emit = transients.append
        
        for index, rise in crossings:
    
            if self._state == _STATE_DOWN:
    
                if rise:
                    # rise while down
    
                    # Start new transient.
                    self._start_index = index
                    self._state = _STATE_UP
    
                # Do nothing for fall while down.
    
            elif self._state == _STATE_UP:
    
                if rise:
                    # rise while up
    
                    if index == self._start_index + self._max_length:
                        # rise just past end of maximal transient
                        
                        # Emit maximal transient.
                        emit((self._start_index, self._max_length))
                        
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
                        
                    elif index > self._start_index + self._max_length:
                        # rise more than one sample past end of maximal
                        # transient
    
                        # Emit maximal transient
                        emit((self._start_index, self._max_length))
    
                        # Start new transient.
                        self._start_index = index
    
                    # Do nothing for rise before end of maximal transient.
    
                else:
                    # fall while up
    
                    if index < self._start_index + self._min_length:
                        # fall before end of minimal transient
    
                        self._state = _STATE_HOLDING
    
                    else:
                        # fall at or after end of minimal transient
    
                        length = index - self._start_index
    
                        # Truncate transient if after end of maximal transient.
                        if length > self._max_length:
                            length = self._max_length
    
                        # Emit transient.
                        emit((self._start_index, length))
                        
                        self._state = _STATE_DOWN
    
            else:
                # holding after short transient
    
                if rise:
                    # rise while holding after short transient
    
                    if index > self._start_index + self._min_length:
                        # rise follows end of minimal transient by at least
                        # one non-transient sample
                        
                        # Emit minimal transient.
                        emit((self._start_index, self._min_length))
    
                        # Start new transient.
                        self._start_index = index
                        
                    self._state = _STATE_UP
    
                else:
                    # fall while holding after short transient
    
                    if index >= self._start_index + self._min_length:
                        # fall at or after end of minimal transient
    
                        # Emit minimal transient.
                        emit((self._start_index, self._min_length))
    
                        self._state = _STATE_DOWN
    
                    # Do nothing for fall before end of minimal transient.

        return transients
    
    
class _ClipBoundsSetter(_SeriesProcessor):
    
    
    def __init__(self, initial_padding, length):
        self._initial_padding = initial_padding
        self._length = length
        
        
    def process(self, clips):
        return [self._set_bounds(clip) for clip in clips]
    
    
    # TODO: Should we do something special if the clip end index is past
    # the signal end index? We currently don't worry about this.
    def _set_bounds(self, clip):
        start_index, _ = clip
        start_index = max(start_index - self._initial_padding, 0)
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
    
    
class TseepDetector(_Detector):
    
    
    extension_name = 'PNF 2017 Basic Tseep Detector 1.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_TSEEP_SETTINGS, sample_rate, listener)

    
class ThrushDetector(_Detector):
    
    
    extension_name = 'PNF 2017 Basic Thrush Detector 1.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_THRUSH_SETTINGS, sample_rate, listener)
        
        
def _firls(numtaps, bands, desired):
    
    """
    Designs an FIR filter that is optimum in a least squares sense.
    
    This function is like `scipy.signal.firls` except that `numtaps`
    can be even as well as odd and band weighting is not supported.
    """
    
    # TODO: Add support for band weighting and then submit a pull
    # request to improve `scipy.signal.firls`.
    
    numtaps = int(numtaps)
    if numtaps % 2 == 1:
        return signal.firls(numtaps, bands, desired)
    else:
        return _firls_even(numtaps, bands, desired)
    
    
def _firls_even(numtaps, bands, desired):
    
    # This function implements an algorithm similar to the one of the
    # SciPy `firls` function, but for even-length filters rather than
    # odd-length ones. See paper notes entitled "Least squares FIR
    # filter design for even N" for derivation. The derivation is
    # similar to that of Ivan Selesnick's "Linear-Phase FIR Filter
    # Design By Least Squares" (available online at
    # http://cnx.org/contents/eb1ecb35-03a9-4610-ba87-41cd771c95f2@7),
    # with due alteration of detail for even filter lengths.
    
    bands.shape = (-1, 2)
    desired.shape = (-1, 2)
    weights = np.ones(len(desired))
    M = int(numtaps / 2)
    
    # Compute M x M matrix Q (actually twice Q).
    n = np.arange(numtaps)[:, np.newaxis, np.newaxis]
    q = np.dot(np.diff(np.sinc(bands * n) * bands, axis=2)[:, :, 0], weights)
    Q1 = linalg.toeplitz(q[:M])
    Q2 = linalg.hankel(q[1:M + 1], q[M:])
    Q = Q1 + Q2
    
    # Compute M-vector b.
    k = np.arange(M) + .5
    e = bands[1]
    b = np.diff(e * np.sinc(e * k[:, np.newaxis])).reshape(-1)
    
    # Compute a (actually half a).
    a = np.dot(linalg.pinv(Q), b)
    
    # Compute h.
    h = np.concatenate((np.flipud(a), a))
    
    return h
