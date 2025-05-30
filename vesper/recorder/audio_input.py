"""Module containing `AudioInput` class."""


import math
# import time

import sounddevice as sd

from vesper.recorder.audio_input_buffer import (
    AudioInputBuffer, AudioInputBufferOverflow)
from vesper.recorder.audio_input_chunk import AUDIO_INPUT_CHUNK_TYPES
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


# TODO: Handle unsupported input sample rates better on macOS.
# See `sounddevice` issue number 505
# (https://github.com/spatialaudio/python-sounddevice/issues/505).
# Note that the issue described there does not seem to be a problem
# on Windows and Linux.


_DEFAULT_SAMPLE_FORMAT = 'int16'
_DEFAULT_PORT_AUDIO_BLOCK_SIZE = 0          # seconds
_DEFAULT_INPUT_BUFFER_CAPACITY = 30         # chunks
_DEFAULT_INPUT_CHUNK_SIZE = 1               # seconds


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
    def parse_settings(settings):

        device_name = settings.get_required('device_name')

        host_api_name = settings.get('host_api_name')

        device = _find_input_device(device_name, host_api_name)

        channel_count = int(settings.get_required('channel_count'))

        if channel_count > device.max_channel_count:
            raise ValueError(
                f'Invalid input channel count {channel_count}. '
                f'For the input device "{device.name}", the maximum '
                f'channel count is {device.max_channel_count}.')
        
        sample_rate = float(settings.get_required('sample_rate'))

        sample_format = settings.get('sample_format', _DEFAULT_SAMPLE_FORMAT)

        if not sample_format in AUDIO_INPUT_CHUNK_TYPES:
            formats = sorted(AUDIO_INPUT_CHUNK_TYPES.keys())
            text = '{' + ', '.join(f'"{f}"' for f in formats) + '}'
            raise ValueError(
                f'Unrecognized audio input sample format "{sample_format}". '
                f'The recognized formats are {text}.')

        sd.check_input_settings(
            device=device.index,
            channels=channel_count,
            samplerate=sample_rate,
            dtype=sample_format)
        
        port_audio_block_size = float(settings.get(
            'port_audio_block_size', _DEFAULT_PORT_AUDIO_BLOCK_SIZE))

        buffer_capacity = int(settings.get(
            'buffer_capacity', _DEFAULT_INPUT_BUFFER_CAPACITY))
        
        chunk_size = float(settings.get(
            'chunk_size', _DEFAULT_INPUT_CHUNK_SIZE))
        
        return Bunch(
            device=device,
            channel_count=channel_count,
            sample_rate=sample_rate,
            sample_format=sample_format,
            port_audio_block_size=port_audio_block_size,
            buffer_capacity=buffer_capacity,
            chunk_size=chunk_size)


    def __init__(
            self, recorder, device, channel_count, sample_rate,
            sample_format, port_audio_block_size, buffer_capacity,
            chunk_size):
        
        self._recorder = recorder
        self._device = device
        self._channel_count = channel_count
        self._sample_rate = sample_rate
        self._sample_format = sample_format
        self._port_audio_block_size = port_audio_block_size
        self._buffer_capacity = buffer_capacity
        self._chunk_size = chunk_size

        # Get list of available input devices, sorted by device name
        # and host API name.
        self._devices = _get_input_devices()
        
        # Get the total number of host APIs used by the available input
        # devices.
        self._host_api_count = \
            len(set([d.host_api_index for d in self._devices]))
        
        # Get the PortAudio block size in sample frames, rounding up.
        self._port_audio_block_size_frames = \
            int(math.ceil(self._port_audio_block_size * self._sample_rate))
        
        self._chunk_type = AUDIO_INPUT_CHUNK_TYPES[self._sample_format]

        # Get the chunk size in sample frames, rounding up.
        self._chunk_size_frames = \
            int(math.ceil(self._chunk_size * self._sample_rate))
        
        self._input_buffer = AudioInputBuffer(
            self.channel_count, self._buffer_capacity,
            self._chunk_size_frames, self._chunk_type)
        
        self._running = False
            
    
    @property
    def recorder(self):
        return self._recorder
    

    @property
    def device(self):
        return self._device
    
    
    @property
    def channel_count(self):
        return self._channel_count
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def sample_format(self):
        return self._sample_format
    

    @property
    def port_audio_block_size(self):
        return self._port_audio_block_size
    

    @property
    def buffer_capacity(self):
        return self._buffer_capacity
    

    @property
    def chunk_size(self):
        return self._chunk_size
    
    
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

            self._stream = sd.RawInputStream(
                device=self.device.index,
                channels=self.channel_count,
                samplerate=self.sample_rate,
                dtype=self.sample_format,
                blocksize=self._port_audio_block_size_frames,
                callback=self._input_callback)
            
            self._stream.start()
    

    def _input_callback(self, samples, frame_count, time_info, status_flags):
        
        # print(f'input_callback {frame_count} {self._callback_count}')
        self._callback_count += 1

        if self._running:
            
            # Comment out for production.
            # self._overflow_test.tick()
            
            port_audio_overflow = status_flags.input_overflow
        
            try:
                self._input_buffer.write(samples, frame_count)

            except AudioInputBufferOverflow as e:

                self._recorder.handle_input_overflow(
                    e.overflow_size, port_audio_overflow)
                
            else:
                # input buffer did not overflow
                
                chunk = self._input_buffer.get_chunk()

                if chunk is not None:
                    self._recorder.process_input(chunk, port_audio_overflow)


    def free_chunk(self, chunk):
        self._input_buffer.free_chunk(chunk)


    def stop(self):
        
        if self._running:
            
            self._running = False
            
            self._stream.stop()
            self._stream.close()


    def get_status_tables(self):
        device_table = self._create_device_table()
        input_table = self._create_input_table()
        return [device_table, input_table]
    

    def _create_device_table(self):
        
        include_host_api_column = self._host_api_count > 1
        selected_device = self.device

        if len(self._devices) == 0:
            header = None
            rows = None
            footer = '<p>No input devices found.</p>'
        
        else:

            if include_host_api_column:
                header = ('Device Name', 'Host API Name', 'Max Channel Count')
            else:
                header = ('Device Name', 'Max Channel Count')

            rows = [
                self._create_device_table_row(
                    d, include_host_api_column, selected_device)
                for d in self._devices]
            
            footer = '* Selected input device.'
        
        return StatusTable('Available Input Devices', rows, header, footer)

    
    def _create_device_table_row(
            self, device, include_host_api_column, selected_device):
        
        prefix = '*' if device.index == selected_device.index else ''
        device_name = prefix + device.name

        if include_host_api_column:
            return (
                device_name, device.host_api_name, device.max_channel_count)
        else:
            return (device_name, device.max_channel_count)
    
    
    def _create_input_table(self):
        
        device = self.device

        device_rows = (('Device Name', device.name),)
        if self._host_api_count > 1:
            device_rows += (('Host API Name', device.host_api_name),)

        # Show PortAudio block size only if it isn't zero.
        if self.port_audio_block_size == 0:
            port_audio_rows = ()
        else:
            port_audio_rows = (
                ('PortAudio Block Size (seconds)',
                 self.port_audio_block_size),)

        rows = device_rows + (
            ('Channel Count', self.channel_count),
            ('Sample Rate (Hz)', self.sample_rate)) + \
            port_audio_rows + (
            ('Buffer Capacity (chunks)', self.buffer_capacity),
            ('Chunk Size (seconds)', self.chunk_size))

        return StatusTable('Input', rows)
    

def _find_input_device(device_name, host_api_name):

    devices = _get_input_devices()

    device_count = len(devices)

    if device_count == 0:
        raise ValueError('No audio input devices found.')
    
    matching_devices = \
        [d for d in devices if _device_matches(d, device_name, host_api_name)]
    
    match_count = len(matching_devices)

    if match_count != 1:

        if match_count == 0:
            prefix = f'Unrecognized'
        else:
            prefix = f'Ambiguous'

        if host_api_name is None:
            spec_type = f'input device name "{device_name}"'
        else:
            spec_type = (
                f'input device name / host API name combination '
                f'({device_name}, {host_api_name})')

        problem = f'{prefix} {spec_type}.'

        lines = [f'    ({d.name}, {d.host_api_name})\n' for d in devices]
        device_table = ''.join(lines)

        remedy = (
            f'Please specify an input device name (and a host API name '
            f'if the device can be accessed via more than one host API) '
            f'that matches exactly one available input device / host API '
            f'combination. The available input device name / host '
            f'API name combinations are:\n\n'
            f'{device_table}\n'
            f'Please see the documentation for the input "device_name" '
            f'and "host_api_name" settings in the example "Vesper '
            f'Recorder Settings.yaml" file for more details.')

        raise ValueError(f'{problem} {remedy}')
    
    else:
        return matching_devices[0]


def _get_input_devices():
    
    # Get input device info.
    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    
    # Get default input device index.
    default_device_index = sd.default.device[0]

    # Get host APIs info.
    host_apis = sd.query_hostapis()

    # Get input device `Bunch` objects.
    devices = [
        _get_input_device(device, default_device_index, host_apis)
        for device in input_devices]
    
    # Sort input devices by name and host API.
    devices.sort(key=lambda d: (d.name, d.host_api_name))

    return devices
    
    
def _get_input_device(device, default_device_index, host_apis):

    host_api_index = device['hostapi']
    host_api = host_apis[host_api_index]
    host_api_name = host_api['name']

    return Bunch(
        index=device['index'],
        name=device['name'],
        is_default=device['index'] == default_device_index,
        host_api_index=host_api_index,
        host_api_name=host_api_name,
        max_channel_count=device['max_input_channels'],
        default_sample_rate=device['default_samplerate'],
        default_low_input_latency=device['default_low_input_latency'],
        default_high_input_latency=device['default_high_input_latency'])
    

def _device_matches(device, device_name, host_api_name):

    if device.name.find(device_name) == -1:
        # `device_name` is not part or all of `device.name`

        return False
    
    else:
        # `device_name` is part or all of `device.name`
        
        # If `host_api_name` is specified, require that it be
        # `device.host_api_name` to match.
        return host_api_name is None or device.host_api_name == host_api_name


# class _PortAudioOverflowTest:
    
    
#     def __init__(self, recorder, duration):
#         self._recorder = recorder
#         self._duration = duration
#         self._slept = False
        
        
#     def tick(self):
#         if not self._slept:
#             time.sleep(self._duration)
#             self._slept = True
        
        
# class _RecorderOverflowTest:
    
    
#     def __init__(self, recorder, duration):
         
#         self._recorder = recorder
#         self._duration = duration
        
#         # Hide recorder's input buffers from audio input callback.
#         self._buffers = []
#         while True:
#             try:
#                 buffer = self._recorder._free_buffer_queue.get(block=False)
#             except Empty:
#                 break
#             else:
#                 self._buffers.append(buffer)
                 
#         self._buffer_count = 0
 
 
#     def tick(self):
         
#         if self._buffer_count < self._duration:
#             self._buffer_count += 1
             
#         else:
             
#             # Unhide free buffers.
#             for buffer in self._buffers:
#                 self._recorder._free_buffer_queue.put(buffer)
