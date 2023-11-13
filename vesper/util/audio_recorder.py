"""Module containing the `AudioRecorder` class."""


from queue import Empty, Queue
from threading import Thread
from datetime import datetime, timedelta, timezone
import math
import time

import sounddevice as sd

from vesper.util.bunch import Bunch
from vesper.util.notifier import Notifier
from vesper.util.schedule import ScheduleRunner


_SAMPLE_SIZE = 2               # bytes


# TODO: Handle unsupported input configurations (e.g. unsupported
# sample rates) gracefully and informatively.

# TODO: Consider eliminating `get_input_devices` function in favor of
# using `sounddevice` functions directly.

# TODO: Consider making default input device the selected input device
# if the specified input device index is not valid.

# TODO: Allow input device specification by name or portion of name in
# configuration. If specified device does not exist or is not unique,
# fall back on default device.

# TODO: Show configuration error messages in red text on web page.

# TODO: Use `sounddevice` default input stream block size of zero. To enable
# this, write incoming samples to a single large (e.g. one minute) circular
# buffer instead of to a fixed-size buffer from a buffer pool. Send samples
# to listeners as NumPy views into this circular buffer, or as a view of
# a copied buffer in the rare case where the samples wrap around the end
# of the circular buffer.

# TODO: Consider moving schedule (and all recording control) out of this
# module.

# TODO: Support 24-bit samples.


class AudioRecorder:
    
    """Records audio using the `sounddevice` Python package."""
    
    
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
    # To record audio, an `AudioRecorder` creates a `sounddevice` stream
    # configured to invoke a callback function periodically with input
    # samples. The callback function is invoked on a thread created by
    # `sounddevice`, which we refer to as the *callback thread*. The
    # callback thread is distinct from the recorder thread. The callback
    # function performs a minimal amount of work to construct a command
    # for the recorder thread telling it to process the input samples,
    # and then writes the command to the recorder thread's command queue.
    #
    # TODO: Document recording control, both manual and scheduled.
    

    @staticmethod
    def get_input_devices():
        return _get_input_devices()


    def __init__(
            self, input_device_index, channel_count, sample_rate, buffer_size,
            total_buffer_size, schedule=None):
        
        self._input_device_index = input_device_index
        self._channel_count = channel_count
        self._sample_rate = sample_rate
        self._sample_size = _SAMPLE_SIZE
        self._buffer_size = buffer_size
        self._total_buffer_size = total_buffer_size
        self._schedule = schedule
        
        self._bytes_per_frame = self.channel_count * self.sample_size
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
        
        buffer_count = int(round(self.total_buffer_size / self.buffer_size))
        bytes_per_buffer = self.frames_per_buffer * self._bytes_per_frame
        
        queue = Queue()
        
        for _ in range(buffer_count):
            buffer = bytearray(bytes_per_buffer)
            queue.put(buffer)
            
        return queue
            

    @property
    def input_device_index(self):
        return self._input_device_index
    
    
    @property
    def channel_count(self):
        return self._channel_count
    
    
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
            # self._overflow_test = _PortAudioOverflowTest(self, 2)
            # self._overflow_test = _RecorderOverflowTest(self, 40)
            
            self._notify_listeners('recording_starting', _get_utc_now())
            
            self._recording = True
            self._stop_pending = False

            dtype = f'int{8 * self._sample_size}'

            self._stream = sd.RawInputStream(
                device=self.input_device_index,
                channels=self.channel_count,
                samplerate=self.sample_rate,
                dtype=dtype,
                blocksize=self.frames_per_buffer,
                callback=self._input_callback)
            
            self._callback_count = 0
            self._stream.start()

            self._notify_listeners('recording_started', _get_utc_now())
    

    def _input_callback(self, samples, frame_count, time_info, status_flags):
        
        # TODO: Learn more about `time_info` and CFFI.

        # TODO: Learn more about `status_flags` and handle errors better.
        # `status_flags` is of type `sd.CallbackFlags`. See
        # https://python-sounddevice.readthedocs.io/en/0.4.6/api/misc.html#sounddevice.CallbackFlags
        # https://python-sounddevice.readthedocs.io/en/0.4.6/_modules/sounddevice.html#CallbackFlags.

        # The following is from an older, PyAudio version of the Vesper 
        # Recorder. I have retained it in case it might be useful.
        #
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

        # print(f'input_callback {frame_count} {self._callback_count}')
        self._callback_count += 1

        if self._recording:
            
            # Comment out for production.
            # self._overflow_test.tick()
            
            # Get samples start time.
            buffer_duration = \
                timedelta(seconds=frame_count / self.sample_rate)
            start_time = _get_utc_now() - buffer_duration
                
            port_audio_overflow = status_flags.input_overflow
        
            try:
                
                # Get buffer to copy new samples into.
                buffer = self._free_buffer_queue.get(block=False)
                
            except Empty:
                # no buffers available
                
                # Prepare command for recorder thread.
                command = Bunch(
                    name='input_overflowed',
                    frame_count=frame_count,
                    start_time=start_time,
                    port_audio_overflow=port_audio_overflow)
                
            else:
                # got a buffer
                
                # Copy samples into buffer.
                byte_count = frame_count * self._bytes_per_frame
                buffer[:byte_count] = samples[:byte_count]
                
                # Prepare command for recorder thread.
                command = Bunch(
                    name='input_arrived',
                    samples=buffer,
                    frame_count=frame_count,
                    start_time=start_time,
                    port_audio_overflow=port_audio_overflow)
                
            # Send command to recorder thread.
            self._command_queue.put(command)


    def _on_input_overflowed(self, command):
        
        c = command
        self._notify_listeners(
            'input_overflowed', c.start_time, c.frame_count,
            c.port_audio_overflow)
        
        self._stop_if_pending()
        
        
    def _stop_if_pending(self):
        
        if self._stop_pending:
            
            self._recording = False
            self._stop_pending = False
            
            self._stream.stop()
            self._stream.close()
            
            self._notify_listeners('recording_stopped', _get_utc_now())

        
    def _on_input_arrived(self, command):
        
        c = command
        self._notify_listeners(
            'input_arrived', c.start_time, c.samples, c.frame_count,
            c.port_audio_overflow)
        
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
    
    # Get input devices.
    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    
    # Get default input device index.
    default_device_index = sd.default.device[0]
    
    return [
        _get_input_device_info(device, default_device_index)
        for device in input_devices]
    
    
def _get_input_device_info(device, default_device_index):
    return Bunch(
        host_api_index=device['hostapi'],
        index=device['index'],
        default=device['index'] == default_device_index,
        name=device['name'],
        input_channel_count=device['max_input_channels'],
        default_sample_rate=device['default_samplerate'],
        default_low_input_latency=device['default_low_input_latency'],
        default_high_input_latency=device['default_high_input_latency'])
    

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
            self, recorder, time, samples, frame_count, port_audio_overflow):
        pass
    
    
    def input_overflowed(
            self, recorder, time, frame_count, port_audio_overflow):
        pass
    
        
    def recording_stopped(self, recorder, time):
        pass


class _PortAudioOverflowTest:
    
    
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
        
        # Hide recorder's input buffers from audio input callback.
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
