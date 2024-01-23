"""Module containing `AudioInput` class."""


import time

import sounddevice as sd

from vesper.recorder.audio_input_buffer import (
    AudioInputBuffer, AudioInputBufferOverflow)
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


# TODO: Handle unsupported input sample rates better on macOS.
# See `sounddevice` issue number 505
# (https://github.com/spatialaudio/python-sounddevice/issues/505).
# Note that the issue described there does not seem to be a problem
# on Windows and Linux.


_DEFAULT_INPUT_BUFFER_SIZE = 10             # seconds
_DEFAULT_INPUT_CHUNK_SIZE = .5              # seconds

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

        sd.check_input_settings(
            device=device.index,
            channels=channel_count,
            samplerate=sample_rate,
            dtype=_SAMPLE_DTYPE)
        
        buffer_size = float(settings.get(
            'buffer_size', _DEFAULT_INPUT_BUFFER_SIZE))
        
        chunk_size = float(settings.get(
            'chunk_size', _DEFAULT_INPUT_CHUNK_SIZE))
        
        return Bunch(
            device=device,
            channel_count=channel_count,
            sample_rate=sample_rate,
            sample_type='int16',
            buffer_size=buffer_size,
            chunk_size=chunk_size)


    def __init__(
            self, recorder, device, channel_count, sample_rate, buffer_size,
            chunk_size):
        
        self._recorder = recorder
        self._device = device
        self._channel_count = channel_count
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._chunk_size = chunk_size

        # Get list of available input devices, sorted by device name
        # and host API name.
        self._devices = _get_input_devices()
        
        # Get the total number of host APIs used by the available input
        # devices.
        self._host_api_count = \
            len(set([d.host_api_index for d in self._devices]))

        chunk_count = int(round(self._buffer_size / self._chunk_size))
        self._chunk_size_frames = \
            int(round(self._chunk_size * self._sample_rate))
        self._frame_size = self.channel_count * _SAMPLE_SIZE // 8
            
        self._input_buffer = AudioInputBuffer(
            chunk_count, self._chunk_size_frames, self._frame_size)
        
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
    def buffer_size(self):
        return self._buffer_size
    

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
                dtype=_SAMPLE_DTYPE,
                blocksize=0,
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
                self._input_buffer.write(samples, frame_count)

            except AudioInputBufferOverflow as e:

                self._recorder.handle_input_overflow(
                    e.overflow_size, port_audio_overflow)
                
            else:
                # input buffer did not overflow
                
                chunk = self._input_buffer.get_chunk()

                if chunk is not None:
                    self._recorder.process_input(
                        chunk, self._chunk_size_frames, port_audio_overflow)


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

        rows = device_rows + (
            ('Channel Count', self.channel_count),
            ('Sample Rate (Hz)', self.sample_rate),
            ('Buffer Size (seconds)', self.buffer_size))

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
