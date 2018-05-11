"""
Module containing multi-threshold reimplementations of Old Bird Tseep and
Thrush detectors.

The implementations in this module run detectors for multiple thresholds
at once for detector evaluations. The implementations eliminate redundant
computation that would be performed if the single-threshold detectors of
the `old_bird_detector_redux_1_1` module were simply run repeatedly with
different thresholds.

The original Old Bird detectors were implemented in the late 1990's by
Steve Mitchell and Bill Evans using the MathWorks' Simulink and Real-Time
Workshop. They were based on an algorithm developed in 1994 by Harold Mills
at the Biocaoustics Research Program of the Cornell Lab of Ornithology. The
reimplementations are writen in Python and make use of NumPy and SciPy.

The original detectors ran only on Windows, could process only input
sampled at 22050 hertz, and could process only one file at a time on a
given computer.  The reimplementations remove all of these restrictions.
"""


import math

import numpy as np
import scipy.linalg as linalg
import scipy.signal as signal

from vesper.util.bunch import Bunch


_OLD_FS = 22050.
"""
the sample rate of the original Old Bird detectors, in hertz.

The reimplemented detectors can operate on input of a variety of sample
rates. We use the sample rate of the original detectors only to convert
detector settings that were originally specified in units of sample
periods to units of seconds.
"""


_TSEEP_SETTINGS = Bunch(
    filter_f0=6000,                     # hertz
    filter_f1=10000,                    # hertz
    filter_bw=100,                      # hertz
    filter_duration=100 / _OLD_FS,      # seconds
    integration_time=2000 / _OLD_FS,    # seconds
    ratio_delay=.02,                    # seconds
    ratio_threshold=2,                  # dimensionless
    min_duration=.100,                  # seconds
    max_duration=.400,                  # seconds
    initial_padding=3000 / _OLD_FS,     # seconds
    suppressor_count_threshold=15,      # clips
    suppressor_period=20                # seconds
)


_THRUSH_SETTINGS = Bunch(
    filter_f0=2800,                     # hertz
    filter_f1=5000,                     # hertz
    filter_bw=100,                      # hertz
    filter_duration=100 / _OLD_FS,      # seconds
    integration_time=4000 / _OLD_FS,    # seconds
    ratio_delay=.02,                    # seconds
    ratio_threshold=1.3,                # dimensionless
    min_duration=.100,                  # seconds
    max_duration=.400,                  # seconds
    initial_padding=5000 / _OLD_FS,     # seconds
    suppressor_count_threshold=10,      # clips
    suppressor_period=20                # seconds
)


# import datetime
# 
# 
# _START_TIME = datetime.datetime(2017, 7, 1, 20)
# 
# 
# def _get_dt(index, sample_rate):
#     td = datetime.timedelta(seconds=index / sample_rate)
#     return _START_TIME + td
#     
#     
# class _CrossingsHandler:
#     
#     
#     def __init__(self, sample_rate):
#         self._sample_rate = sample_rate
#         
#         
#     def handle_crossings(self, crossings, lines):
#         
#         for index, rise in crossings:
#             direction = 'Rise' if rise else 'Fall'
#             start_time = _get_dt(index, self._sample_rate)
#             s = '{} {}'.format(direction, str(start_time))
#             lines.append((index, s))
        
        
class _Detector:
    
    """
    Reimplementation of Old Bird transient detector.
    
    The original Old Bird Tseep and Thrush detectors were implemented in
    the late 1990's by Steve Mitchell and Bill Evans using the MathWorks'
    Simulink and Real-Time Workshop. The detectors were based on a transient
    detection algorithm developed in 1994 by Harold Mills at the Bioacoustics
    Research Program of the Cornell Lab of Ornithology. The Tseep and Thrush
    detectors used the same basic transient detection algorithm, but with
    different settings.
    
    The Old Bird detectors had a number of limitations. For example, they
    ran only on Windows, they assumed an input sample rate of 22050 hertz,
    and they could only run on one input file on a given computer at once.
    This reimplementation removes those limitations.
    
    An instance of this class operates on a single audio channel. It has a
    `detect` method that takes a NumPy array of samples. The method can be
    called repeatedly with consecutive sample arrays. The `complete_detection`
    method should be called after the final call to the `detect` method.
    During detection, each time the detector detects a clip it notifies
    a listener by invoking the listener's `process_clip` method. The
    `process_clip` method must accept two arguments, the start index and
    length of the detected clip.
    
    See the `_TSEEP_SETTINGS` and `_THRUSH_SETTINGS` objects above for
    settings that make a `_Detector` behave much like the original Old
    Bird Tseep and Thrush detectors in the sense that it will detect
    most of the same clips. The `TseepDetector` and `ThrushDetector`
    classes of this module subclass the `_Detector` class with fixed
    settings, namely `_TSEEP_SETTINGS` AND `_THRUSH_SETTINGS`,
    respectively.
    
    This detector reimplementation was developed and tested initially in
    the GitHub repository https://github.com/HaroldMills/Vesper-Tseep-Thrush,
    and then copied to the Vesper repository for further development and
    testing. See the README of the Vesper-Tseep-Thrush repository for more
    about the reimplementation effort.
    """
    
    
    def __init__(self, settings, ratio_thresholds, sample_rate, listener):
        
        self._settings = settings
        self._ratio_thresholds = ratio_thresholds
        self._sample_rate = sample_rate
        self._listener = listener
        
        self._signal_processor = self._create_signal_processor()
        self._series_processors = self._create_series_processors()
        
        self._num_samples_processed = 0
        self._recent_samples = np.array([], dtype='float')
        self._initial_samples_repeated = False
        
#         self._crossings_handler = _CrossingsHandler(sample_rate)
#         self._lines = []
        
    
    def _create_signal_processor(self):
        
        coefficients = self._design_filter()
        
        s = self.settings
        
        integration_length = int(round(s.integration_time * self.sample_rate))
        
        # We use `math.floor` here rather than `round` since the Simulink
        # .mdl files we have access to suggest that the original Old Bird
        # detectors use MATLAB's `fix`  function, which rounds towards zero.
        delay = math.floor(s.ratio_delay * self.sample_rate)
        
        processors = [
            _FirFilter(coefficients),
            _Squarer(),
            _Integrator(integration_length),
            _Divider(delay),
        ]
        
        return _SignalProcessorChain(processors)
        
        
    def _design_filter(self):
        
        s = self.settings
        
        # We use a filter length that is proportional to the sample rate,
        # and that is 100 when the sample rate is 22050 hertz. (The original
        # Old Bird detectors were intended for 22050 hertz input only, and
        # their filters had length 100.)
        #
        # Varying the filter length in this way yields filters with very
        # similar frequency responses at different sample rates. See the
        # Jupyter notebook
        # "Old Bird Detector Filter at Different Sample Rates.ipynb" in
        # the "HaroldMills/Vesper-Tseep-Thrush" GitHub repository for a
        # demonstration of this for the Tseep and Thrush detector filters..
        filter_length = int(round(s.filter_duration * self.sample_rate))
        
        f0 = s.filter_f0
        f1 = s.filter_f1
        bw = s.filter_bw
        fs2 = self.sample_rate / 2
        bands = np.array([0, f0 - bw, f0, f1, f1 + bw, fs2]) / fs2
        
        desired = np.array([0, 0, 1, 1, 0, 0])
        
        return _firls(filter_length, bands, desired)
    
    
    def _create_series_processors(self):
        return dict(
            (t, self._create_series_processors_aux())
            for t in self._ratio_thresholds)
    
    
    def _create_series_processors_aux(self):
        
        s = self.settings
        sample_rate = self.sample_rate
        
        # We use `math.floor` here rather than `round` since the Simulink
        # .mdl files we have access to suggest that the original Old Bird
        # detectors use MATLAB's `fix`  function, which rounds toward zero.
        min_length = int(math.floor(s.min_duration * sample_rate))
        max_length = int(math.floor(s.max_duration * sample_rate))
        
        initial_padding = int(round(s.initial_padding * sample_rate))
        
        suppressor_period = int(round(s.suppressor_period * sample_rate))
        
        processors = [
            _TransientFinder(min_length, max_length),
            _ClipExtender(initial_padding),
            # _ClipMerger(),
            # _ClipSuppressor(s.suppressor_count_threshold, suppressor_period),
            # _ClipTruncator(),
            _ClipShifter(-initial_padding)
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
                
            # Add one to offset for agreement with original Old Bird detector.
            offset += 1
                
            for threshold in self._ratio_thresholds:
                
                crossings = \
                    self._get_threshold_crossings(ratios, threshold, offset)
                
                # self._crossings_handler.handle_crossings(
                #     crossings, self._lines)
                
                clips = self._series_processors[threshold].process(crossings)
                
                self._notify_listener(clips, threshold)
                
            # Save trailing samples for next call to this method.
            self._recent_samples = \
                augmented_samples[-self._signal_processor.latency:]
            
        self._num_samples_processed += len(samples)
            
            
    def _get_threshold_crossings(self, ratios, threshold, offset):
    
        # Add one to index offset to compensate for processing latency
        # of this method.
        offset += 1
        
        x0 = ratios[:-1]
        x1 = ratios[1:]
        
        # Find indices where ratio rises above threshold.
        t = threshold
        rise_indices = np.where((x0 <= t) & (x1 > t))[0] + offset
        
        # Find indices where ratio falls below threshold inverse.
        t = 1 / t
        fall_indices = np.where((x0 >= t) & (x1 < t))[0] + offset

        # Tag rises and falls with booleans, combine, and sort.
        return sorted(
            [(i, True) for i in rise_indices] +
            [(i, False) for i in fall_indices])
    
    
    def _notify_listener(self, clips, threshold):
        
        for start_index, length in clips:
            
#             start_time = _get_dt(start_index, self.sample_rate)
#             start_time += datetime.timedelta(seconds=3000 / self.sample_rate)
#             end_time = _get_dt(start_index + length, self.sample_rate)
#             duration = (length - 3000) / self.sample_rate
#             s = '{} {} {} {}'.format(
#                 length, str(start_time), duration, str(end_time))
#             self._lines.append((start_index, s))

            self._listener.process_clip(start_index, length, threshold)
            
            
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
        for threshold, processor in self._series_processors.items():
            clips = processor.complete_processing([fall])
            self._notify_listener(clips, threshold)

#         self._lines.sort()
#         text = ''.join('{} {}\n'.format(i, s) for i, s in self._lines)
#         with open(r'C:\Users\Harold\Desktop\Detector Output.txt', 'w') as f:
#             f.write(text)
        

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
                        # source code file splimflipflop.c), and our goal
                        # here is to reimplement that detector. This code
                        # should seldom execute on real inputs, since it
                        # should be rare for two consecutive rises to occur
                        # precisely `self._max_length` samples apart.
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
    
    
class _ClipExtender(_SeriesProcessor):
    
    
    def __init__(self, extension_length):
        self._extension_length = extension_length
        
        
    def process(self, clips):
        return [self._extend_clip(clip) for clip in clips]
    
    
    def _extend_clip(self, clip):
        start_index, length = clip
        return (start_index, length + self._extension_length)
            
        
class _ClipMerger(_SeriesProcessor):
    
    
    def __init__(self):
        self._prev_start_index = None
        self._prev_end_index = None
        
        
    def process(self, clips):
        
        merged_clips = []
        
        for start_index, length in clips:
            
            if self._prev_start_index is None:
                # first clip
                 
                self._remember_clip(start_index, length)
                 
            elif start_index <= self._prev_end_index:
                # not first clip, and new clip overlaps or immediately
                # follows previous clip
                     
                # Merge new clip into previous clip.
                self._prev_end_index = start_index + length
                     
            else:
                # not first clip, new clip does not overlap previous clip
                 
                self._append_previous_clip(merged_clips)
                self._remember_clip(start_index, length)
                
        return merged_clips
    
    
    def _remember_clip(self, start_index, length):
        self._prev_start_index = start_index
        self._prev_end_index = start_index + length
        

    def _append_previous_clip(self, clips):
        prev_length = self._prev_end_index - self._prev_start_index
        clips.append((self._prev_start_index, prev_length))
        

    def complete_processing(self, clips):
        
        merged_clips = self.process(clips)
        
        if self._prev_start_index is not None:
            # one more clip to emit
            
            self._append_previous_clip(merged_clips)
            
        return merged_clips

        
class _ClipSuppressor(_SeriesProcessor):
    
    
    def __init__(self, count_threshold, period):
        self._count_threshold = count_threshold
        self._period = period
        self._recent_start_indices = []
        
        
    def process(self, clips):
        
        unsuppressed_clips = []
        
        indices = self._recent_start_indices
             
        for start_index, length in clips:
            
            # Remember clip.
            indices.append(start_index)
             
            # Discard oldest clip if there are more than count threshold.
            if len(indices) > self._count_threshold:
                indices.pop(0)
                 
            if len(indices) == self._count_threshold:
                # have enough clips to test for suppression
                 
                delta = (indices[-1] - indices[0])
                 
                if delta < self._period:
                    # got more than `self._count_threshold` clips in the
                    # last `self._period` samples
                     
                    # Suppress clip.
                    continue
                 
            # If we get here, the clip was not suppressed.
            unsuppressed_clips.append((start_index, length))
            
        return unsuppressed_clips
        
        
_BUFFER_SIZE = 8192
_FIFO_SIZE = 4 * _BUFFER_SIZE
_OVERLAP_SIZE = _FIFO_SIZE - _BUFFER_SIZE


class _ClipTruncator(_SeriesProcessor):
    
    
    def process(self, clips):
        
        processed_clips = []
        
        for start_index, length in clips:
            
            end_index = start_index + length
            
            final_segment_length = end_index % _BUFFER_SIZE
            
            initial_segment_length = \
                min(length - final_segment_length, _OVERLAP_SIZE)
                
            length = initial_segment_length + final_segment_length
            
            start_index = end_index - length
            
            processed_clips.append((start_index, length))
            
        return processed_clips
            
    
class _ClipShifter(_SeriesProcessor):
    
    
    def __init__(self, shift):
        self._shift = shift
        
        
    def process(self, clips):
        return [self._shift_clip(clip) for clip in clips]
    
    
    def _shift_clip(self, clip):
        start_index, length = clip
        start_index = max(start_index + self._shift, 0)
        return (start_index, length)
            
        
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
    
    
    extension_name = 'Old Bird Tseep Detector Redux 1.1'
    
    
    def __init__(self, thresholds, sample_rate, listener):
        super().__init__(_TSEEP_SETTINGS, thresholds, sample_rate, listener)

    
class ThrushDetector(_Detector):
    
    
    extension_name = 'Old Bird Thrush Detector Redux 1.1'
    
    
    def __init__(self, thresholds, sample_rate, listener):
        super().__init__(_THRUSH_SETTINGS, thresholds, sample_rate, listener)
        
        
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
