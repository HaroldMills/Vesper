"""Module containing the `AudioRecorder` class."""


from queue import Empty, Queue
from threading import Thread
from datetime import datetime, timedelta, timezone
import math
import time

import pyaudio
from pyaudio import paInputOverflow

from vesper.util.bunch import Bunch
from vesper.util.notifier import Notifier
from vesper.util.schedule import ScheduleRunner


_SAMPLE_SIZE = 2               # bytes


class AudioRecorder:
    
    """Records audio asynchronously."""
    
    
    # Most of the work of an `AudioRecorder` is performed by a thread
    # called the *recorder thread*. The recorder thread is created by
    # the recorder when it it initialized, and runs as long as the process
    # in which it was started. The recorder thread receives *commands*
    # via an associated FIFO *command queue*, and processes the commands
    # in the order in which they are received. The queue is synchronized,
    # so commands can safely be written to it by any number of threads,
    # but only the recorder thread reads the queue and executes the
    # commands.
    #
    # To record audio, an `AudioRecorder` creates a PyAudio stream
    # configured to invoke a callback function periodically with input
    # samples. The callback function is invoked on a thread created by
    # PyAudio, which we refer to as the *callback thread*. The callback
    # thread is distinct from the recorder thread. The callback function
    # performs a minimal amount of work to construct a command for the
    # recorder thread telling it to process the input samples, and then
    # writes the command to the recorder thread's command queue.
    #
    # TODO: Document recording control, both manual and scheduled.
    

    @staticmethod
    def get_input_devices():
        return _get_input_devices()


    def __init__(
            self, input_device_index, num_channels, sample_rate, buffer_size,
            total_buffer_size, schedule=None):
        
        self._input_device_index = input_device_index
        self._num_channels = num_channels
        self._sample_rate = sample_rate
        self._sample_size = _SAMPLE_SIZE
        self._buffer_size = buffer_size
        self._total_buffer_size = total_buffer_size
        self._schedule = schedule
        
        self._bytes_per_frame = self.num_channels * self.sample_size
        self._frames_per_buffer = \
            int(math.ceil(self.buffer_size * self.sample_rate))
            
        self._free_buffer_queue = self._create_input_buffers()
            
        self._recording = False
        self._stop_pending = False
        
        self._notifier = Notifier()
        
        self._command_queue = Queue()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

        if schedule is not None:
            self._schedule_runner = ScheduleRunner(schedule)
            listener = _ScheduleListener(self)
            self._schedule_runner.add_listener(listener)
        else:
            self._schedule_runner = None
            
    
    def _create_input_buffers(self):
        
        """
        Creates input buffers to hold up to `self.total_buffer_size`
        seconds of samples and puts them onto free buffer queue.
        """
        
        num_buffers = int(round(self.total_buffer_size / self.buffer_size))
        bytes_per_buffer = self.frames_per_buffer * self._bytes_per_frame
        
        queue = Queue()
        
        for _ in range(num_buffers):
            buffer = bytearray(bytes_per_buffer)
            queue.put(buffer)
            
        return queue
            

    @property
    def input_device_index(self):
        return self._input_device_index
    
    
    @property
    def num_channels(self):
        return self._num_channels
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def sample_size(self):
        return self._sample_size
    
    
    @property
    def buffer_size(self):
        return self._buffer_size
    
    
    @property
    def frames_per_buffer(self):
        return self._frames_per_buffer


    @property
    def total_buffer_size(self):
        return self._total_buffer_size
    
    
    @property
    def schedule(self):
        return self._schedule
    
    
    @property
    def recording(self):
        return self._recording
    
    
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
    
    
    def remove_listener(self, listener):
        self._notifier.remove_listener(listener)
    
    
    def clear_listeners(self):
        self._notifier.clear_listeners()
    
    
    def _notify_listeners(self, method_name, *args, **kwargs):
        self._notifier.notify_listeners(method_name, self, *args, **kwargs)
            
            
    def start(self):
        if self._schedule_runner is not None:
            self._schedule_runner.start()
        else:
            self._start()
                
                
    def _start(self):
        command = Bunch(name='start')
        self._command_queue.put(command)
            
    
    def stop(self):
        if self._schedule_runner is not None:
            self._schedule_runner.stop()
        else:
            self._stop()
                
                
    def _stop(self):
        command = Bunch(name='stop')
        self._command_queue.put(command)
            
            
    def _run(self):
        
        # TODO: What do we do if this method raises an exception?
        
        while True:
            
            # Read next command.
            command = self._command_queue.get()

            # Execute command.
            handler_name = '_on_' + command.name
            handler = getattr(self, handler_name)
            handler(command)
                
    
    def _on_start(self, command):
        
        if not self._recording:
            
            # Comment out for production.
            # self._overflow_test = _PyAudioOverflowTest(self, 2)
            # self._overflow_test = _RecorderOverflowTest(self, 40)
            
            self._pyaudio = pyaudio.PyAudio()
            
            self._notify_listeners('recording_starting', _get_utc_now())
            
            self._recording = True
            self._stop_pending = False

            self._stream = self._pyaudio.open(
                input=True,
                input_device_index=self.input_device_index,
                channels=self.num_channels,
                rate=self.sample_rate,
                format=pyaudio.paInt16,
                frames_per_buffer=self.frames_per_buffer,
                stream_callback=self._pyaudio_callback)
            
            self._notify_listeners('recording_started', _get_utc_now())
    

    def _pyaudio_callback(self, samples, num_frames, time_info, status_flags):
        
        # Recording input latency and buffer ADC times as reported by PyAudio
        # do not appear to be useful, at least as of 2017-01-30 on a Windows
        # 10 VM running on Parallels 11 on Mac OS X El Capitan.
        #
        # Recording input latencies reported by the
        # `pyaudio.Stream.get_input_latency` method were .5 seconds when
        # the input buffer size was one second or more, and were the
        # buffer size when it was one half second or less. These are
        # unreasonably high, and are not consistent with an upper bound
        # of tens of milliseconds measured as the time elapsed from just
        # before an input stream was started to the time when its first
        # buffer arrived, minus the buffer size of one second.
        #
        # Again from tests with various buffer sizes, it appears that the
        # `'current_time'` value in the `time_info` argument to this method
        # is always zero, and that the `'input_buffer_adc_time'` is always
        # the latency reported by `pyaudio.Stream.get_input_latency` minus
        # the buffer size.
        #
        # What we really want is the actual start time of each sample buffer.
        # Without a simple way to get that time we report to listeners the
        # times just before and after the input stream starts and the time
        # at the beginning of each execution of the callback method, and
        # leave it to them to try to compute more accurate buffer start times
        # from those data if they wish.

        if self._recording:
            
            # Comment out for production.
            # self._overflow_test.tick()
            
            # Get samples start time.
            buffer_duration = \
                timedelta(seconds=num_frames / self.sample_rate)
            start_time = _get_utc_now() - buffer_duration
                
            pyaudio_overflow = (status_flags & paInputOverflow) != 0
        
            try:
                
                # Get buffer to copy new samples into.
                buffer = self._free_buffer_queue.get(block=False)
                
            except Empty:
                # no buffers available
                
                # Prepare command for recorder thread.
                command = Bunch(
                    name='input_overflowed',
                    num_frames=num_frames,
                    start_time=start_time,
                    pyaudio_overflow=pyaudio_overflow)
                
            else:
                # got a buffer
                
                # Copy samples into buffer.
                num_bytes = num_frames * self._bytes_per_frame
                buffer[:num_bytes] = samples[:num_bytes]
                
                # Prepare command for recorder thread.
                command = Bunch(
                    name='input_arrived',
                    samples=buffer,
                    num_frames=num_frames,
                    start_time=start_time,
                    pyaudio_overflow=pyaudio_overflow)
                
            # Send command to recorder thread.
            self._command_queue.put(command)
                
            return (None, pyaudio.paContinue)
        
        else:
            return (None, pyaudio.paComplete)


    def _on_input_overflowed(self, command):
        
        c = command
        self._notify_listeners(
            'input_overflowed', c.start_time, c.num_frames,
            c.pyaudio_overflow)
        
        self._stop_if_pending()
        
        
    def _stop_if_pending(self):
        
        if self._stop_pending:
            
            self._recording = False
            self._stop_pending = False
            
            self._stream.stop_stream()
            self._stream.close()
            self._pyaudio.terminate()
            
            self._notify_listeners('recording_stopped', _get_utc_now())

        
    def _on_input_arrived(self, command):
        
        c = command
        self._notify_listeners(
            'input_arrived', c.start_time, c.samples, c.num_frames,
            c.pyaudio_overflow)
        
        # Free sample buffer for reuse.
        self._free_buffer_queue.put(c.samples)
        
        self._stop_if_pending()


    def _on_stop(self, command):
        
        # Instead of stopping recording here, we just set a flag
        # indicating that a stop is pending, and then stop in the
        # next call to the`_on_input` method *after* processing
        # the next buffer of input samples. If we stop here we
        # usually record one less buffer than one would expect.
        if self._recording:
            self._stop_pending = True
    

    def wait(self, timeout=None):
        if self._schedule_runner is not None:
            self._schedule_runner.wait(timeout)


def _get_input_devices():
    
    pa = pyaudio.PyAudio()
    
    # Get host APIs.
    n = pa.get_host_api_count()
    host_api_infos = [pa.get_host_api_info_by_index(i) for i in range(n)]
    host_api_names = dict((i['index'], i['name']) for i in host_api_infos)
        
    # Get devices.
    n = pa.get_device_count()
    device_infos = [pa.get_device_info_by_index(i) for i in range(n)]
    
    # Get default input device index.
    try:
        default_device_info = pa.get_default_input_device_info()
    except IOError:
        default_index = -1
    else:
        default_index = default_device_info['index']

    pa.terminate()

    return tuple(
        _get_input_device(i, default_index, host_api_names)
        for i in device_infos if i['maxInputChannels'] != 0)
    
    
def _get_input_device(info, default_index, host_api_names):
    return Bunch(
        host_api_name=host_api_names[info['hostApi']],
        index=info['index'],
        default=info['index'] == default_index,
        name=info['name'],
        num_input_channels=info['maxInputChannels'],
        default_sample_rate=info['defaultSampleRate'],
        default_low_input_latency=info['defaultLowInputLatency'],
        default_high_input_latency=info['defaultHighInputLatency'])
    

def _get_utc_now():
    return datetime.fromtimestamp(time.time(), timezone.utc)


class _ScheduleListener:
    
    
    def __init__(self, recorder):
        self._recorder = recorder
        
        
    def schedule_run_started(self, schedule, time, state):
        if state:
            self._recorder._start()
    
    
    def schedule_state_changed(self, schedule, time, state):
        if state:
            self._recorder._start()
        else:
            self._recorder._stop()
    
    
    def schedule_run_stopped(self, schedule, time, state):
        self._recorder._stop()
    
    
    def schedule_run_completed(self, schedule, time, state):
        self._recorder._stop()


class AudioRecorderListener:
    
    """
    Listener for events generated by an audio recorder.
    
    The default implementations of the methods of this class do nothing.
    """
    
    
    def recording_starting(self, recorder, time):
        pass
    
    
    def recording_started(self, recorder, time):
        pass
    
    
    def input_arrived(
            self, recorder, time, samples, num_frames, pyaudio_overflow):
        pass
    
    
    def input_overflowed(self, recorder, time, num_frames, pyaudio_overflow):
        pass
    
        
    def recording_stopped(self, recorder, time):
        pass


class _PyAudioOverflowTest:
    
    
    def __init__(self, recorder, duration):
        self._recorder = recorder
        self._duration = duration
        self._slept = False
        
        
    def tick(self):
        if not self._slept:
            time.sleep(self._duration)
            self._slept = True
        
        
class _RecorderOverflowTest:
    
    
    def __init__(self, recorder, duration):
         
        self._recorder = recorder
        self._duration = duration
        
        # Hide recorder's input buffers from PyAudio callback.
        self._buffers = []
        while True:
            try:
                buffer = self._recorder._free_buffer_queue.get(block=False)
            except Empty:
                break
            else:
                self._buffers.append(buffer)
                 
        self._buffer_count = 0
 
 
    def tick(self):
         
        if self._buffer_count < self._duration:
            self._buffer_count += 1
             
        else:
             
            # Unhide free buffers.
            for buffer in self._buffers:
                self._recorder._free_buffer_queue.put(buffer)
