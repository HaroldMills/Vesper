"""Module containing `AudioInput` class."""


from queue import Empty, Queue
import math
import time

import sounddevice as sd

from vesper.util.bunch import Bunch
import vesper.util.text_utils as text_utils


# TODO: Handle unsupported input sample rates better on macOS.
# See `sounddevice` issue number 505
# (https://github.com/spatialaudio/python-sounddevice/issues/505).
# Note that the issue described there does not seem to be a problem
# on Windows and Linux.

# TODO: Use `sounddevice` default input stream block size of zero. To enable
# this, write incoming samples to a single large (e.g. one minute) circular
# buffer instead of to a fixed-size buffer from a buffer pool. Send samples
# to listeners as NumPy views into this circular buffer, or as a view of
# a copied buffer in the rare case where the samples wrap around the end
# of the circular buffer.


_USE_RAW_STREAM = False

_SAMPLE_SIZE = 16
_SAMPLE_DTYPE = 'int16'


class AudioInput:
    
    """
    Provides audio input for the Vesper Recorder using the `sounddevice`
    Python package.

    Most of the work of the Vesper Recorder is performed by a thread
    called the *main thread*. The main thread is created by the
    recorder when it it initialized, and runs as long as the process
    in which it was started. The main thread receives *commands* via
    an associated FIFO *command queue*, and processes the commands
    in the order in which they are received. The queue is synchronized,
    so commands can safely be written to it by any number of threads,
    but only the main thread reads the queue and executes the commands.
    
    To produce audio samples, an `AudioInput` creates a `sounddevice`
    stream configured to invoke a callback function periodically with
    the input samples. The callback function is invoked on a thread
    created by `sounddevice`, which we refer to as the *input thread*.
    The input thread is distinct from the main thread of the recorder,
    which executes commands submitted to it on a thread-safe queue.
    The callback function performs a minimal amount of work to construct
    a command for the main thread telling it to process the input samples,
    and then writes the command to the command queue.
    """
    

    @staticmethod
    def get_input_devices():
        return _get_input_devices()
    

    @staticmethod
    def check_input_settings(settings):

        _check_input_device_name(settings.device_name)

        sd.check_input_settings(
            device=settings.device_name,
            channels=settings.channel_count,
            samplerate=settings.sample_rate,
            dtype=_SAMPLE_DTYPE)


    def __init__(
            self, recorder, input_device_name, channel_count, sample_rate,
            buffer_size, total_buffer_size):
        
        self._recorder = recorder
        self._input_device_name = input_device_name
        self._channel_count = channel_count
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._total_buffer_size = total_buffer_size
        
        self._bytes_per_frame = self.channel_count * _SAMPLE_SIZE // 8
        self._frames_per_buffer = \
            int(math.ceil(self.buffer_size * self.sample_rate))
            
        self._free_buffer_queue = self._create_input_buffers()
            
        self._running = False
            
    
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
    def recorder(self):
        return self._recorder
    

    @property
    def input_device_name(self):
        return self._input_device_name
    
    
    @property
    def channel_count(self):
        return self._channel_count
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
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
    def running(self):
        return self._running
    
    
    def start(self):
        
        if not self._running:
            
            # Comment out for production.
            # self._overflow_test = _PortAudioOverflowTest(self, 2)
            # self._overflow_test = _RecorderOverflowTest(self, 40)
            
            self._running = True
            self._callback_count = 0

            if _USE_RAW_STREAM:
                # use raw input stream, which delivers raw sample bytes
                # to input callback.

                stream_class = sd.RawInputStream

            else:
                # use regular input stream, which delivers samples in
                # NumPy arrays to callback.

                stream_class = sd.InputStream

            self._stream = stream_class(
                device=self.input_device_name,
                channels=self.channel_count,
                samplerate=self.sample_rate,
                dtype=_SAMPLE_DTYPE,
                blocksize=self.frames_per_buffer,
                callback=self._input_callback)
            
            self._stream.start()
    

    def _input_callback(self, samples, frame_count, time_info, status_flags):
        
        # TODO: Learn more about `time_info` and CFFI.

        # TODO: Learn more about `status_flags` and handle errors better.
        # `status_flags` is of type `sd.CallbackFlags`. See
        # https://python-sounddevice.readthedocs.io/en/0.4.6/api/misc.html#sounddevice.CallbackFlags
        # https://python-sounddevice.readthedocs.io/en/0.4.6/_modules/sounddevice.html#CallbackFlags.

        # print(f'input_callback {frame_count} {self._callback_count}')
        self._callback_count += 1

        if self._running:
            
            # Comment out for production.
            # self._overflow_test.tick()
            
            port_audio_overflow = status_flags.input_overflow
        
            try:
                
                # Get buffer to copy new samples into.
                buffer = self._free_buffer_queue.get(block=False)
                
            except Empty:
                # no buffers available
                
                self._recorder.handle_input_overflow(
                    frame_count, port_audio_overflow)
                
            else:
                # got a buffer
                
                if not _USE_RAW_STREAM:
                    # `samples` is a NumPy array.

                    # Get raw sample bytes.
                    samples = samples.tobytes()

                # Copy samples into buffer.
                byte_count = frame_count * self._bytes_per_frame
                buffer[:byte_count] = samples[:byte_count]
                
                self._recorder.process_input(
                    buffer, frame_count, port_audio_overflow)


    def free_buffer(self, buffer):
        self._free_buffer_queue.put(buffer)


    def stop(self):
        
        if self._running:
            
            self._running = False
            
            self._stream.stop()
            self._stream.close()


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
    

def _check_input_device_name(name):

    devices = _get_input_devices()
    names = sorted(d.name for d in devices)

    matching_names = [n for n in names if n.find(name) != -1]
    match_count = len(matching_names)

    if match_count != 1:

        names = text_utils.create_string_item_list(f'"{n}"' for n in names)

        if match_count == 0:
            prefix = 'Unrecognized'
        
        elif match_count > 1:
            prefix = 'Ambiguous'
    
        raise ValueError(
            f'{prefix} input device name "{name}". Please specify a '
            f'name or name portion that matches exactly one device name. '
            f'Valid names are {names}.')

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
