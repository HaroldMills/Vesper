"""
Module containing PNF energy detector.

The detector looks for transients in the energy within a specific frequency
band of a spectrogram, and produces a clip for each transient found.

The `TseepDetector` and `ThrushDetector` classes of this module have
detector parameter values appropriate for tseep and thrush nocturnal
flight calls, respectively.
"""


# TODO: Modify detector interface to support any number of listeners.


import numpy as np
import scipy.signal as signal

from vesper.util.bunch import Bunch
from vesper.util.detection_score_file_writer import DetectionScoreFileWriter
import vesper.util.time_frequency_analysis_utils as tfa_utils


'''
Notes regarding parameter values
--------------------------------

I explored various options for detector parameter values, evaluating
the resulting detectors on the BirdVox-full-night recordings since
those evaluations can be automated. To make the search tractable, I
varies only one or two parameter values at a time, exploring ranges
of values that seemed reasonable, and verifying that performance
degraded towards the ends of the ranges.

While exploring options for parameter values, I found that changing
a value would sometimes increase performance in one range of recalls,
while reducing it in another range. I decided to try to maximize
performance for recalls above 25 percent, and especially between 25
and 50 percent, where I expect we will operate.

* Spectrogram

I tried spectrogram window sizes of 4, 5, 6, 7, and 8 ms for the tseep
and thrush detectors, with a hop size of 50 percent. For the tseep
detector, 4 ms performed best, with 5 ms negligibly close behind.
For the thrush detector, 5-8 ms were clustered close to each other,
with 4 ms clearly worse. 5 ms had a precision that was up to about
1.5 percent worse than 6-8 ms for recalls in the range 25-50 percent.

The 5 ms window size has an important computational advantage over
the 6-8 ms sizes. For both the 22050 and 24000 hertz sample rates its
window length is less than 128, while for 6-8 ms it is more than 128.
This means that we would have to use a spectrogram DFT size of 256 for
6-8 ms, but only for the 32000 hertz sample rate for 5 ms. Detection
with a DFT size of 128 should be tens of percent faster than detection
with a DFT size of 256, assuming that the spectrogram computation
dominates the cost.

I chose a window size of 5 ms for both detectors. I want them to share a
window size and hop size if that doesn't hinder performance much, so that
we will have the option of computing the spectrogram once for both
detectors. We can't do that now due to a limitation of the Vesper
detection infrastructure, but if that limitation is removed then sharing
the spectrogram computation between the detectors will provide a big
efficiency boost.

I tried hop sizes of 50, 75, and 100 percent for both detectors with a
window size of 5 ms. 50 percent was a little better than 75 percent for
both detectors, while performance for 100 percent was poor. I chose the
50 percent hop size mainly out of conservatism, I think: I find it
difficult to trust a spectrogram with a hop size of more than 50 percent,
since it skips over some of the input. There would be considerable
computational advantage to a larger hop size, though. Perhaps tweaking
the power filter for the 75 percent hop size would help?

I tried Hann, Hamming, Blackman, and Nuttall windows for both detectors
with a window size of 5 ms. The Hann, Blackman, and Nuttall windows
performed very similarly, and the Hamming window a little less well.

* Frequency range

I experimented with extending the tseep detector frequency range,
lowering 6000 hertz to 5500 and 5000 hertz and raising 10000 hertz to
11000 hertz in various combinations. The best option seemed to be
5000-10000 hertz, which is consistent with the call frequencies I
see when I look at clip albums of the BirdVox-full-night dataset.

I also experimented with modifying the thrush detector frequency range.
I tried various start frequencies ranging from 2000 to 3000, and found
that 2600 seemed best. This is consistent with the observation that
many thrush calls include portions below 2800 hertz, down to the low
2000's. I'm a little surprised that it was not advantageous to lower
the start frequency even more, but apparently doing that results in
enough additional false detections to make it not worthwhile. With
a good coarse classifier, would it be advantageous to lower the
start frequency even more?

I tried thrush detector end frequencies ranging from 3000 to 5000.
Lower frequencies improved the precision-recall curves, in some
cases dramatically, but I decided to leave the frequency at 5000,
at least for now, since some PNF calls (e.g. for American Pipit)
seem to go that high. I will discuss this with Debbie and Bill.

* Power filter

In the original Old Bird detectors, the power filters just sum
consecutive powers: they are crude lowpass FIR filters whose
coefficients are all ones. In designing this detector I found that
performance was superior for recalls above 25 percent if we used
a lowpass filter designed as such.

I considered both FIR and IIR designs for the power filters, and
shorter FIR filters worked best. I think IIR filters didn't work as
well because their effective impulse response length (in some sense
related to how quickly the response decays) is too large. We are
detecting transients, which limits the length of useful filters.
It is easier to control the length of an FIR filter than the
effective length of the impulse response of an IIR filter.

Somewhat surprisingly (and accidentally), I found that FIR filters
of a given length designed by the least squares method outperform
those designed by the Remez algorithm. I believe that is because
the stopband lobes of a least squares filter decay more rapidly than
those of a Remez filter (which, of course, don't fall off at all):
only the first stopband lobe of a Remez filter is lower than the
corresponding lobe of a least squares filter.

For the tseep detector, FIR filters of length 23-47 performed more
or less identically for recalls above 25 percent (and very similarly
below that). I chose a length of 31 since it's toward the middle of
that range and I assume that keeping the length smaller than 32
will make the FFT-based fast convolution used to implement the
filter a little faster.

I experimented with various combinations of power filter passband
end and stopband start frequencies for the tseep detector, and found
that 5 and 15 hertz seem to work well, respectively.

* Delay

For the tseep detector, I tried delays ranging from 30 to 90.
The curves for 50, 60, and 70 were very similar, with the one for
50 being (very slightly) the best.

For the thrush detector, I tried delays ranging from 50 to 200.
80 was the best, with 70, 90, and 100 very close behind.

* Transient finder

I tried a more complicated version of the transient finder for
the tseep detector that ignored upward threshold crossings during
a suppression period (50 or 100 ms, say) following an initial
threshold crossing. This helped only very little (a maximum increase
of perhaps 1 percent precision at a given recall) for a power filter
passband end frequency of 10 Hz, and negligibly for one of 5 Hz, so
I opted for the simpler version.

* Thresholds

To choose thresholds for the two detectors, I looked at the CSV
output from the evaluate_detectors script to find the closest two-digit
threshold near the threshold with the largest F1 value. In both cases
the the detector with the chosen threshold (2.5 for thrush and 2.7 for
tseep) has both higher recall and higher precision the baseline detector.
'''


'''
Algorithmic ideas I'd like to try:

* Estimate background noise level using order statistics rather than
averaging. See Numpy's percentile function.

* Use an unconventional spectrogram window with a larger passband
(designed with firls or remez) and detect separately in overlapping
frequency ranges (one for each spectrogram bin). The smaller frequency
ranges would give us higher SNR. How would we aggregate the results
from the different sub-detectors?
'''
    
    
_TSEEP_SETTINGS = Bunch(
    window_type='hann',
    window_size=.005,                           # seconds
    hop_size=50,                                # percent
    start_frequency=5000,                       # hertz
    end_frequency=10000,                        # hertz
    power_filter_passband_end_frequency=5,      # hertz
    power_filter_stopband_start_frequency=15,   # hertz
    power_filter_length=31,                     # samples
    delay=.050,                                 # seconds
    thresholds=[2.7],                           # dimensionless
    initial_clip_padding=.050,                  # seconds
    clip_duration=.300                          # seconds
)


_THRUSH_SETTINGS = Bunch(
    window_type='hann',
    window_size=.005,                           # seconds
    hop_size=50,                                # percent
    start_frequency=2600,                       # hertz
    end_frequency=5000,                         # hertz
    power_filter_passband_end_frequency=5,      # hertz
    power_filter_stopband_start_frequency=15,   # hertz
    power_filter_length=31,                     # samples
    delay=.080,                                 # seconds
    thresholds=[2.5],                           # dimensionless
    initial_clip_padding=.050,                  # seconds
    clip_duration=.400                          # seconds
)


_WRITE_DETECTION_SCORE_FILE = False
"""
`True` if detectors should write input audio and detection scores to a
stereo audio file. This feature is for test purposes only: for normal
operation such output should be disabled.
"""


class Detector:
    
    """
    PNF energy detector.

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
        
        if _WRITE_DETECTION_SCORE_FILE:
            file_name = f'{self.extension_name} Audio and Scores.wav'
            file_path = f'/Users/harold/Desktop/{file_name}'
            score_scale_factor = 1000
            hop_size = self._signal_processor.hop_size
            self._detection_score_file_writer = DetectionScoreFileWriter(
                file_path, input_sample_rate, score_scale_factor, hop_size)
         

    def _create_signal_processor(self):
        
        s = self.settings
        
        fs = self._input_sample_rate
        window_size = _seconds_to_samples(s.window_size, fs)
        hop_size = _seconds_to_samples(s.window_size * s.hop_size / 100, fs)
        dft_size = tfa_utils.get_dft_size(window_size)
        spectrograph = _Spectrograph(
            'Spectrograph', s.window_type, window_size, hop_size, dft_size, fs)
        
        bin_size = spectrograph.bin_size
        start_bin_num = _get_start_bin_num(s.start_frequency, bin_size)
        end_bin_num = _get_end_bin_num(s.end_frequency, bin_size)
        frequency_integrator = _FrequencyIntegrator(
            'Frequency Integrator', start_bin_num, end_bin_num,
            spectrograph.output_sample_rate)
        
        fs = frequency_integrator.output_sample_rate
        power_filter = self._create_power_filter(fs)
        
        fs = power_filter.output_sample_rate
        delay = _seconds_to_samples(s.delay, fs)
        divider = _Divider('Divider', delay, fs)
        
        processors = [
            spectrograph,
            frequency_integrator,
            power_filter,
            divider
        ]
        
        return _SignalProcessorChain(
            'Detector', processors, self._input_sample_rate,
            self._debugging_listener)
        

    def _create_power_filter(self, input_sample_rate):
        
        s = self.settings
        
        return _FirPowerFilter(
            'Power Filter', s.power_filter_passband_end_frequency,
            s.power_filter_stopband_start_frequency, s.power_filter_length,
            input_sample_rate)
        
#         return _IirPowerFilter(
#             'Power Filter', s.power_filter_passband_end_frequency,
#             s.power_filter_stopband_start_frequency, input_sample_rate)


    def _create_series_processors(self):
        return dict(
            (t, self._create_series_processors_aux())
            for t in self._settings.thresholds)
    
    
    def _create_series_processors_aux(self):
        
        s = self.settings
        
        return _Clipper(
            s.initial_clip_padding, s.clip_duration,
            self._input_sample_rate)
    
        
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
           
        for threshold in self._settings.thresholds:
            crossings = self._get_threshold_crossings(ratios, threshold)
            clips = self._series_processors[threshold].process(crossings)
            self._notify_listener(clips, threshold)
            
        num_samples_generated = len(ratios)
        num_samples_processed = \
            num_samples_generated * self._signal_processor.hop_size
            
        if _WRITE_DETECTION_SCORE_FILE:
            self._detection_score_file_writer.write(
                samples[:num_samples_processed], ratios)
          
        self._num_samples_processed += num_samples_processed
        self._unprocessed_samples = samples[num_samples_processed:]
        self._num_samples_generated += num_samples_generated
            
            
    def _get_threshold_crossings(self, ratios, threshold):
      
        x0 = ratios[:-1]
        x1 = ratios[1:]
          
        # Find indices where ratio rises above threshold.
        t = threshold
        indices = np.where((x0 <= t) & (x1 > t))[0] + 1
          
        # Convert indices to times.
        times = self._convert_indices_to_times(indices)
        
        # Get ratios at times as detection scores.
        scores = x1[indices - 1]
        
        return list(zip(times, scores))
    
    
    def _convert_indices_to_times(self, indices):
        input_fs = self._signal_processor.input_sample_rate
        output_fs = self._signal_processor.output_sample_rate
        offset = self._num_samples_processed / input_fs + \
            self._signal_processor.output_time_offset
        return indices / output_fs + offset
    
    
    def _notify_listener(self, clips, threshold):
        for start_index, length, score in clips:
            annotations = {'Detector Score': score}
            self._listener.process_clip(
                start_index, length, threshold, annotations)
            
            
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        for threshold, processor in self._series_processors.items():
            
            clips = processor.complete_processing([])
            self._notify_listener(clips, threshold)
            
            if hasattr(self._listener, 'complete_processing'):
                self._listener.complete_processing(threshold)
                
        if _WRITE_DETECTION_SCORE_FILE:
            self._detection_score_file_writer.close()
        

def _seconds_to_samples(duration, sample_rate):
    return int(round(duration * sample_rate))


def _get_start_bin_num(frequency, bin_size):
    
    """
    Gets the number of the frequency bin whose lower edge is closest to
    the specified frequency.
    """
    
    # The desired bin is the one whose center frequency is closest to
    # the specified frequency plus half the bin size.
    
    return _get_bin_num(frequency + bin_size / 2, bin_size)


def _get_bin_num(frequency, bin_size):
    
    """
    Gets the number of the frequency bin whose center is closest to
    the specified frequency.
    """
    
    return int(round(frequency / bin_size))


def _get_end_bin_num(frequency, bin_size):
    
    """
    Gets the number of the frequency bin whose upper edge is closest to
    the specified frequency.
    """
    
    # The desired bin is the one whose center frequency is closest to
    # the specified frequency minus half the bin size.
    
    return _get_bin_num(frequency - bin_size / 2, bin_size)


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
            self, name, window_type, window_size, hop_size, dft_size,
            input_sample_rate):
        
        super().__init__(name, window_size, hop_size, input_sample_rate)
        
        self.window = signal.get_window(window_type, window_size)
        # self.window = HannWindow(window_size).samples
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
     
     
class _FirPowerFilter(_FirFilter):
    
    
    def __init__(
            self, name, passband_end_frequency, stopband_start_frequency,
            filter_length, input_sample_rate):
        
        fs = input_sample_rate

        # Design filter.
        f_pass = passband_end_frequency
        f_stop = stopband_start_frequency
        bands = np.array([0, f_pass, f_stop, fs / 2])
#         desired = np.array([1, 0])
#         coefficients = signal.remez(filter_length, bands, desired, fs=fs)
        desired = np.array([1, 1, 0, 0])
        coefficients = signal.firls(filter_length, bands, desired, fs=fs)

        super().__init__(name, coefficients, input_sample_rate)

        
class _IirPowerFilter(_SignalProcessor):
    
    
    def __init__(
            self, name, passband_end_frequency, stopband_start_frequency,
            input_sample_rate):
        
        # Design filter.
        fs2 = input_sample_rate / 2
        f_pass = passband_end_frequency / fs2
        f_stop = stopband_start_frequency / fs2
        b, a = signal.iirdesign(f_pass, f_stop, 1, 30, ftype='butter')
        
        super().__init__(name, len(b), 1, input_sample_rate)
        
        # Initialize filter coefficients.
        self._a = a
        self._b = b
        
        # Initialize filter state.
        self._state = np.zeros(max(len(a), len(b)) - 1)


    def process(self, x):
        y, self._state = signal.lfilter(self._b, self._a, x, zi=self._state)
        return y


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
    
    
class _Clipper(_SeriesProcessor):
     
    """Finds transients in a series of threshold crossings."""
     
     
    def __init__(self, initial_clip_padding, clip_duration, sample_rate):
        self._initial_padding = initial_clip_padding
        self._duration = clip_duration
        self._sample_rate = sample_rate
        self._length = _seconds_to_samples(self._duration, self._sample_rate)
                  
         
    def process(self, crossings):
            
        clips = []
            
        for time, score in crossings:
        
            start_time = max(time - self._initial_padding, 0)
            start_index = _seconds_to_samples(
                start_time, self._sample_rate)
            clips.append((start_index, self._length, score))
                  
        return clips


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
    
    
    extension_name = 'PNF Tseep Energy Detector 1.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_TSEEP_SETTINGS, sample_rate, listener)

    
class ThrushDetector(Detector):
    
    
    extension_name = 'PNF Thrush Energy Detector 1.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_THRUSH_SETTINGS, sample_rate, listener)
