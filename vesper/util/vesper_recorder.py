"""Module containing the `VesperRecorder` class."""


from http.server import HTTPServer, BaseHTTPRequestHandler
from logging import FileHandler, Formatter
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo
import datetime
import logging
import math
import os
import wave

import numpy as np

from vesper.util.audio_recorder import AudioRecorder, AudioRecorderListener
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule
import vesper.util.yaml_utils as yaml_utils


# TODO: Review threads involved in recording (schedule, recorder, and server),
# clarify their responsibilities, and improve error handling and shutdown.
# Implement setting updates and remote logging and control. How does
# recording relate to Vesper job system (as of this writing it's completely
# independent, but perhaps it should not be)? How does it relate to other
# processing, like detection and classification, that we would like to be
# able to schedule?


# TODO: Consider allowing level meter to be turned on and off during recording.
# TODO: Specify file duration rather than size.
# TODO: Move scheduling from `AudioRecorder` to `VesperRecorder`.
# TODO: Make saving audio files optional.
# TODO: Consider using a `VesperRecorderError` exception.
# TODO: Make sample size in bits a recorder setting, fixed at 16 for now.
# TODO: Add support for 24-bit samples.
# TODO: Consider adding support for 32-bit floating point samples.
# TODO: Consider adding support for additional file formats, e.g. FLAC.
# TODO: Add support for sample rate conversion.


_HOME_DIR_VAR_NAME = 'VESPER_RECORDER_HOME'
_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_SETTINGS_FILE_NAME = 'Vesper Recorder Settings.yaml'

_AUDIO_FILE_NAME_EXTENSION = '.wav'
_AUDIO_FILE_HEADER_SIZE = 44                # bytes, size of .wav file header

_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_LATITUDE = None
_DEFAULT_LONGITUDE = None
_DEFAULT_TIME_ZONE = 'UTC'
_DEFAULT_CHANNEL_COUNT = 1
_DEFAULT_SAMPLE_RATE = 22050
_DEFAULT_BUFFER_SIZE = .05
_DEFAULT_TOTAL_BUFFER_SIZE = 60
_DEFAULT_LEVEL_METER_ENABLED = True
_DEFAULT_LEVEL_METER_PERIOD = 1             # seconds
_DEFAULT_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_MAX_AUDIO_FILE_SIZE = 2**31        # bytes
_DEFAULT_PORT_NUM = 8001


_logger = logging.getLogger(__name__)


class VesperRecorder:
    
    """Records audio to .wav files according to a schedule."""
    
    
    VERSION_NUMBER = '0.3.0a0'


    @staticmethod
    def get_input_devices():
        return AudioRecorder.get_input_devices()
    
    
    @staticmethod
    def create_and_start_recorder(message):
        return _create_and_start_recorder(message)
    
    
    def __init__(self, settings):
        self._settings = settings

        
    def start(self):
        
        s = self._settings
        
        # Create audio recorder.
        self._recorder = AudioRecorder(
            s.input_device_index, s.channel_count, s.sample_rate,
            s.buffer_size, s.total_buffer_size, s.schedule)
        
        # Create logger.
        self._recorder.add_listener(_Logger())

        # Create level meter if indicated.
        if s.level_meter_enabled:
            level_meter = _AudioLevelMeter(_DEFAULT_LEVEL_METER_PERIOD)
        else:
            level_meter = None
        if level_meter is not None:
            self._recorder.add_listener(level_meter)

        # Create audio file writer.
        self._recorder.add_listener(_AudioFileWriter(
            s.station_name, s.recording_dir_path, s.max_audio_file_size))
         
        # Create HTTP server.
        server = _HttpServer(
            s.port_num, s.station_name, s.lat, s.lon, s.time_zone,
            self._recorder, level_meter, s.recording_dir_path,
            s.max_audio_file_size)
        Thread(target=server.serve_forever, daemon=True).start()

        # Start recording.
        self._recorder.start()
         

    def wait(self, timeout=None):
        self._recorder.wait(timeout)
        
        
    def stop(self):
        self._recorder.stop()
        
        
def _create_and_start_recorder(message):
    
    home_dir_path = os.environ.get(_HOME_DIR_VAR_NAME)
     
    # Use current working directory as home directory if home directory
    # environment variable is not set.
    if home_dir_path is None:
        home_dir_path = Path.cwd()
        _logger.info(
            f'{_HOME_DIR_VAR_NAME} environment variable is not set. '
            f'Will use current working directory "{home_dir_path}" as '
            f'home directory.')
         
    home_dir_path = Path(home_dir_path)

    # Check that home directory exists.
    if not home_dir_path.exists():
        _logger.error(
            f'Recorder home directory "{home_dir_path}" does not exist.')
        return None
    
    # Now that we know that we have a home directory, and hence a place
    # for a log file, add file logging.
    _add_file_logging(home_dir_path)
    
    _logger.info(message)
    
    _logger.info(
        f'Recorder version number is {VesperRecorder.VERSION_NUMBER}.')
    
    settings_file_path = home_dir_path / _SETTINGS_FILE_NAME
        
    # Check that settings file exists.
    if not settings_file_path.exists():
        _logger.error(
            f'Recorder settings file "{settings_file_path}" does not exist.')
        return None
        
    # Parse settings file.
    try:
        settings = _parse_settings_file(settings_file_path, home_dir_path)
    except Exception as e:
        _logger.error(
            f'Could not parse recorder settings file '
            f'"{settings_file_path}". Error message was: {e}')
        return None
    
    _logger.info(
        f'Starting recorder with HTTP server at port {settings.port_num}.')
    
    # Create recorder.
    try:
        recorder = VesperRecorder(settings)
    except Exception as e:
        _logger.error(f'Could not create recorder. Error message was: {e}')
        return None
           
    # Start recorder. 
    try:
        recorder.start()
    except Exception as e:
        _logger.error(f'Could not start recorder. Error message was: {e}')
        return None
    
    # Phew. We made it!
    return recorder
        

def _add_file_logging(home_dir_path):
    
    # Create handler that appends messages to log file.
    log_file_path = home_dir_path / _LOG_FILE_NAME
    handler = FileHandler(log_file_path)
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to root logger.
    logger = logging.getLogger()
    logger.addHandler(handler)
        
        
def _parse_settings_file(file_path, home_dir_path):
    
    with open(file_path) as f:
        settings = yaml_utils.load(f)
        
    station_name = settings.get('station', _DEFAULT_STATION_NAME)
    
    lat = settings.get('latitude', _DEFAULT_LATITUDE)
    if lat is not None:
        lat = float(lat)
        
    lon = settings.get('longitude', _DEFAULT_LONGITUDE)
    if lon is not None:
        lon = float(lon)
        
    time_zone = ZoneInfo(settings.get('time_zone', _DEFAULT_TIME_ZONE))
        
    # TODO: Consider allowing specification of input device by name
    # or name portion. Would have to handle non-uniqueness.
    input_device_index = int(settings.get('input_device'))
    channel_count = int(settings.get('channel_count', _DEFAULT_CHANNEL_COUNT))
    sample_rate = int(settings.get('sample_rate', _DEFAULT_SAMPLE_RATE))
    buffer_size = float(settings.get('buffer_size', _DEFAULT_BUFFER_SIZE))
    total_buffer_size = \
        float(settings.get('total_buffer_size', _DEFAULT_TOTAL_BUFFER_SIZE))
    
    schedule_dict = settings.get('schedule', {})
    schedule = Schedule.compile_dict(
        schedule_dict, latitude=lat, longitude=lon, time_zone=time_zone)
    
    level_meter_enabled = settings.get(
        'level_meter_enabled', _DEFAULT_LEVEL_METER_ENABLED)
    
    recording_dir_path = Path(
        settings.get('recording_dir_path', _DEFAULT_RECORDING_DIR_PATH))
    if not recording_dir_path.is_absolute():
        recording_dir_path = home_dir_path / recording_dir_path
        
    max_audio_file_size = settings.get(
        'max_audio_file_size', _DEFAULT_MAX_AUDIO_FILE_SIZE)
    
    port_num = int(settings.get('port_num', _DEFAULT_PORT_NUM))
    
    return Bunch(
        station_name=station_name,
        lat=lat,
        lon=lon,
        time_zone=time_zone,
        input_device_index=input_device_index,
        channel_count=channel_count,
        sample_rate=sample_rate,
        buffer_size=buffer_size,
        total_buffer_size=total_buffer_size,
        schedule=schedule,
        level_meter_enabled=level_meter_enabled,
        recording_dir_path=recording_dir_path,
        max_audio_file_size=max_audio_file_size,
        port_num=port_num)
    
    
class _Logger(AudioRecorderListener):
    
    
    def __init__(self):
        super().__init__()
        self._portaudio_overflow_buffer_count = 0
        self._recorder_overflow_frame_count = 0
        
        
    def recording_started(self, recorder, time):
        self._sample_rate = recorder.sample_rate
        _logger.info('Started recording.')
        
        
    def input_arrived(
            self, recorder, time, samples, frame_count, portaudio_overflow):
        
        self._log_portaudio_overflow_if_needed(portaudio_overflow)
        self._log_recorder_overflow_if_needed(False)
            
            
    def _log_portaudio_overflow_if_needed(self, overflow):
        
        if overflow:
            
            if self._portaudio_overflow_buffer_count == 0:
                # overflow has just started
                
                _logger.error(
                    'PortAudio input overflow: PortAudio has reported that '
                    'an unspecified number of input samples were dropped '
                    'before or during the current buffer. A second message '
                    'will be logged later indicating the number of '
                    'consecutive buffers for which this error occurred.')
                
            self._portaudio_overflow_buffer_count += 1
            
        else:
            
            if self._portaudio_overflow_buffer_count > 0:
                # overflow has just ended
                
                if self._portaudio_overflow_buffer_count == 1:
                    
                    _logger.error(
                        'PortAudio input overflow: Overflow was reported for '
                        'one buffer.')
                    
                else:
                    
                    _logger.error(
                        f'PortAudio input overflow: Overflow was reported '
                        f'for {self._portaudio_overflow_buffer_count} '
                        f'consecutive buffers.')
            
                self._portaudio_overflow_buffer_count = 0
            

    def _log_recorder_overflow_if_needed(self, overflow, frame_count=0):
        
        if overflow:
            
            if self._recorder_overflow_frame_count == 0:
                # overflow has just started
                
                _logger.error(
                    'Recorder input overflow: The recorder has run out of '
                    'buffers for arriving input samples. It will substitute '
                    'zero samples until buffers become available, and then '
                    'log another message to report the duration of the lost '
                    'samples.')
                
            self._recorder_overflow_frame_count += frame_count
            
        else:
            
            if self._recorder_overflow_frame_count > 0:
                # overflow has just ended
                
                duration = \
                    self._recorder_overflow_frame_count / self._sample_rate
                _logger.error(
                    f'Recorder input overflow: {duration:.3f} seconds of '
                    f'zero samples were substituted for lost input samples.')
                    
                self._recorder_overflow_frame_count = 0
                    
        
    def input_overflowed(
            self, recorder, time, frame_count, portaudio_overflow):
        self._log_portaudio_overflow_if_needed(portaudio_overflow)
        self._log_recorder_overflow_if_needed(True, frame_count)
        
        
    def recording_stopped(self, recorder, time):
        self._log_portaudio_overflow_if_needed(False)
        self._log_recorder_overflow_if_needed(False)
        _logger.info('Stopped recording.')

    
class _AudioLevelMeter(AudioRecorderListener):


    def __init__(self, update_period):
        self._update_period = update_period
        self._rms_values = None
        self._peak_values = None


    @property
    def rms_values(self):
        return self._rms_values
    

    @property
    def peak_values(self):
        return self._peak_values
    

    def recording_starting(self, recorder, time):

        _logger.info(f'_AudioLevelMeter.recording_starting: {time}')

        self._channel_count = recorder.channel_count
        self._block_size = \
            int(round(recorder.sample_rate * self._update_period))
        self._sums = np.zeros(self._channel_count)
        self._peaks = np.zeros(self._channel_count)
        self._accumulated_frame_count = 0
        self._full_scale_value = 2 ** (recorder.sample_size * 8 - 1)


    def input_arrived(
            self, recorder, time, samples, frame_count, portaudio_overflow):
        
        # TODO: This method allocates memory via NumPy every time it runs.
        # Is that problematic?

        samples = np.frombuffer(samples, dtype='<i2').astype(np.float64)

        # Make sample array 2D.
        samples = samples.reshape((frame_count, self._channel_count))

        # _logger.info(f'_AudioLevelMeter.input_arrived: {time} {frame_count} {samples.shape}')
      
        start_index = 0

        while start_index != frame_count:

            remaining = self._block_size - self._accumulated_frame_count
            n = min(frame_count, remaining)
            
            # Accumulate squared samples.
            s = samples[start_index:start_index + n]
            self._sums += np.sum(s * s, axis=0)

            # Update maximum absolute sample values.
            peaks = np.max(np.abs(samples), axis=0)
            self._peaks = np.maximum(self._peaks, peaks)

            self._accumulated_frame_count += n

            if self._accumulated_frame_count == self._block_size:
                # have accumulated an entire block

                rms_values = np.sqrt(self._sums / self._block_size)
                
                self._rms_values = rms_sample_to_dbfs(
                    rms_values, self._full_scale_value)
                
                self._peak_values = sample_to_dbfs(
                    self._peaks, self._full_scale_value)
                
                _logger.info(
                    f'_AudioLevelMeter: RMS {self._rms_values} '
                    f'peak {self._peak_values}')
                
                self._sums = np.zeros(self._channel_count)
                self._peaks = np.zeros(self._channel_count)
                self._accumulated_frame_count = 0

            start_index += n


    def recording_stopped(self, recorder, time):
       _logger.info(f'_AudioLevelMeter.recording_stopped: {time}')
       self._rms_values = None
       self._peak_values = None
 

class _AudioFileWriter(AudioRecorderListener):
    
    
    def __init__(self, station_name, recording_dir_path, max_file_size):
        
        super().__init__()
        
        self._station_name = station_name
        self._recording_dir_path = recording_dir_path
        self._max_file_size = max_file_size
        
        # Create recording directory if needed.
        self._recording_dir_path.mkdir(parents=True, exist_ok=True)
        
        
    def recording_starting(self, recorder, time):
        
        self._channel_count = recorder.channel_count
        self._sample_rate = recorder.sample_rate
        self._sample_size = recorder.sample_size
        self._frame_size = self._channel_count * self._sample_size
        self._zeros = bytearray(recorder.frames_per_buffer * self._frame_size)
        
        max_audio_byte_count = self._max_file_size - _AUDIO_FILE_HEADER_SIZE
        self._max_file_frame_count = \
            int(math.floor(max_audio_byte_count / self._frame_size))
                    
        self._file_namer = _AudioFileNamer(
            self._station_name, _AUDIO_FILE_NAME_EXTENSION)
        
        self._file = None
        
    
    def input_arrived(
            self, recorder, time, samples, frame_count, portaudio_overflow):
        self._write_samples(time, samples, frame_count)
        
        
    def _write_samples(self, time, samples, frame_count):
        
        remaining_frame_count = frame_count
        buffer_index = 0
        
        while remaining_frame_count != 0:
            
            if self._file is None:
                self._file = self._open_audio_file(time)
                self._file_frame_count = 0
        
            frame_count = min(
                remaining_frame_count,
                self._max_file_frame_count - self._file_frame_count)
                
            byte_count = frame_count * self._frame_size
            
            # TODO: We assume here that the sample bytes are in
            # little-endian order, but perhaps we shouldn't.
            self._file.writeframes(
                samples[buffer_index:buffer_index + byte_count])
            
            remaining_frame_count -= frame_count
            self._file_frame_count += frame_count
            buffer_index += byte_count
            
            if self._file_frame_count == self._max_file_frame_count:
                self._file.close()
                self._file = None
    
    
    def input_overflowed(
            self, recorder, time, frame_count, portaudio_overflow):
        self._write_samples(time, self._zeros, frame_count)
    
        
    def _open_audio_file(self, time):
        
        file_name = self._file_namer.create_file_name(time)
        file_path = self._recording_dir_path / file_name
        
        file_ = wave.open(str(file_path), 'wb')
        file_.setnchannels(self._channel_count)
        file_.setframerate(self._sample_rate)
        file_.setsampwidth(self._sample_size)
        
        return file_
    

    def recording_stopped(self, recorder, time):
        if self._file is not None:
            self._file.close()
        
    
class _AudioFileNamer:
    
    
    def __init__(self, station_name, file_name_extension):
        self.station_name = station_name
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.station_name}_{time}_Z{self.file_name_extension}'
        
        
class _HttpServer(HTTPServer):
    
    
    def __init__(
            self, port_num, station_name, lat, lon, time_zone, recorder,
            level_meter, recording_dir_path, max_audio_file_size):
        
        address = ('', port_num)
        super().__init__(address, _HttpRequestHandler)
        
        self._recording_data = Bunch(
            station_name=station_name,
            lat=lat,
            lon=lon,
            time_zone=time_zone,
            recorder=recorder,
            level_meter=level_meter,
            recording_dir_path=recording_dir_path,
            max_audio_file_size=max_audio_file_size
        )
        
    
_PAGE = '''<!DOCTYPE html>
<html>
<head>
<title>Vesper Recorder</title>
{}
</head>
<body>

<h1>Vesper Recorder {}</h1>

<p>
Welcome to the Vesper Recorder! This page displays information regarding
your recorder. Refresh the page to update the information.
</p>

<h2>Recording Status</h2>
{}

<h2>Station Configuration</h2>
{}

<h2>Input Devices</h2>
{}

<h2>Input Configuration</h2>
{}

<h2>Output Configuration</h2>
{}

<h2>Scheduled Recordings</h2>
{}

</body>
</html>
'''


_CSS = '''
<style>
h2 {
    margin-top: 30px;
    margin-bottom: 5px;
}
table {
    border-collapse: collapse;
    width: 600px;
}
td, th {
    border: 1px solid #a0a0a0;
    text-align: left;
    padding: 8px;
}
tr:nth-child(even) {
    background-color: #d0d0d0;
}
</style>
'''
        
        
class _HttpRequestHandler(BaseHTTPRequestHandler):
    
    
    def do_GET(self):
        
        if self.path == '/':
            body = self._create_status_page_body()
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(body)
            
        else:
            self.send_response(404, 'Not Found')
            self.end_headers()
                    
        
    def _create_status_page_body(self):
        
        data = self.server._recording_data
        recorder = data.recorder
        now = datetime.datetime.now(tz=ZoneInfo('UTC'))
                
        status_table = self._create_status_table(data, recorder, now)
        station_table = self._create_station_table(data)
        devices = recorder.get_input_devices()
        devices_table = self._create_devices_table(devices)
        input_table = self._create_input_table(devices, recorder)
        output_table = self._create_output_table(data)
        recording_table = self._create_recording_table(
            recorder.schedule, data.time_zone, now)
        
        body = _PAGE.format(
            _CSS, VesperRecorder.VERSION_NUMBER, status_table, station_table,
            devices_table, input_table, output_table, recording_table)
        
        return body.encode()
    
    
    def _create_status_table(self, data, recorder, now):
        
        time_zone = data.time_zone
        
        time = _format_datetime(now, time_zone)
        recording = 'Yes' if recorder.recording else 'No'
        
        value_suffix = '' if recorder.channel_count == 1 else 's'
        level_meter = data.level_meter
        if level_meter is not None:
            rms_values = _format_levels(level_meter.rms_values)
            peak_values = _format_levels(level_meter.peak_values)
        
        interval = self._get_status_schedule_interval(recorder.schedule, now)
        
        if interval is None:
            prefix = 'Next'
            start_time = 'None'
            end_time = 'None'
        else:
            start_time = _format_datetime(interval.start, time_zone)
            end_time = _format_datetime(interval.end, time_zone)
            prefix = 'Current' if interval.start <= now else 'Next'
            
        if level_meter is None:
            level_meter_rows = ()
        else:
            level_meter_rows = (
                (f'Recent RMS Sample Value{value_suffix} (dBFS)', rms_values),
                (f'Recent Peak Sample Value{value_suffix} (dBFS)', peak_values)
            )

        rows = (
            ('Time', time),
            ('Recording', recording)
        ) + level_meter_rows + (
            (prefix + ' Recording Start Time', start_time),
            (prefix + ' Recording End Time', end_time)
        )
        
        return _create_table(rows)
        
        
    def _get_status_schedule_interval(self, schedule, time):
        intervals = schedule.get_intervals(start=time)
        try:
            return next(intervals)
        except StopIteration:
            return None
        
        
    def _create_station_table(self, data):
        rows = (
            ('Station Name', data.station_name),
            ('Latitude (degrees north)', data.lat),
            ('Longitude (degrees east)', data.lon),
            ('Time Zone', str(data.time_zone)))
        return _create_table(rows)
    
    
    def _create_devices_table(self, devices):
        
        if len(devices) == 0:
            return '<p>No input devices were found.</p>'
        
        else:
            recorder = self.server._recording_data.recorder
            selected_device_index = recorder.input_device_index
            rows = [
                self._create_devices_table_row(d, selected_device_index)
                for d in devices]
            header = ('Index', 'Name', 'Channel Count')
            table = _create_table(rows, header)
            if selected_device_index < len(devices):
                table += '<p>* Selected input device.</p>'
            return table

    
    def _create_devices_table_row(self, device, selected_device_index):
        prefix = '*' if device.index == selected_device_index else ''
        return (
            prefix + str(device.index), device.name,
            device.input_channel_count)
    
    
    def _create_input_table(self, devices, recorder):
        
        device_dict = {d.index: d for d in devices}
        device_index = recorder.input_device_index
        device = device_dict.get(device_index)

        if device is None:
            device_name = \
                f'There is no input device with index {device_index}.'
        else:
            device_name = device.name
            
        rows = (
            ('Device Index', device_index),
            ('Device Name', device_name),
            ('Channel Count', recorder.channel_count),
            ('Sample Rate (Hz)', recorder.sample_rate),
            ('Buffer Size (seconds)', recorder.buffer_size)
        )
        return _create_table(rows)
    
    
    def _create_output_table(self, data):
        recording_dir_path = data.recording_dir_path.absolute()
        rows = (
            ('Recording Directory', recording_dir_path),
            ('Max Audio File Size (bytes)', data.max_audio_file_size)
        )
        return _create_table(rows)


    def _create_recording_table(self, schedule, time_zone, now):
        rows = [
            self._create_recording_table_row(index, interval, time_zone, now)
            for index, interval in enumerate(schedule.get_intervals())]
        header = ('Index', 'Start Time', 'End Time', 'Status')
        return _create_table(rows, header)
    
    
    def _create_recording_table_row(self, index, interval, time_zone, now):
        start_time = _format_datetime(interval.start, time_zone)
        end_time = _format_datetime(interval.end, time_zone)
        if now > interval.end:
            status = 'Past'
        elif now < interval.start:
            status = 'Future'
        else:
            status = 'Current'
        return (index, start_time, end_time, status)
        
        
def _format_datetime(dt, time_zone=None):
    if time_zone is not None:
        dt = dt.astimezone(time_zone)
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def _format_levels(levels):
    if levels is None:
        return '-'
    else:
        levels = [f'{l:.2f}' for l in levels]
        return ', '.join(levels)


def _create_table(rows, header=None):
    header = _create_table_header(header)
    rows = ''.join(_create_table_row(r) for r in rows)
    return '<table>\n' + header + rows + '</table>\n'


def _create_table_header(items):
    return _create_table_row(items, 'h') if items is not None else ''


def _create_table_row(items, tag_letter='d'):
    items = ''.join(_create_table_item(i, tag_letter) for i in items)
    return '  <tr>\n' + items + '  </tr>\n'
    
    
def _create_table_item(item, tag_letter):
    return f'    <t{tag_letter}>{item}</t{tag_letter}>\n'


# TODO: Move dBFS functions to `signal_utils` package.


_HALF_SQRT_2 = math.sqrt(2) / 2


def sample_to_dbfs(sample, full_scale_value):
    return 20 * np.log10(np.abs(sample) / full_scale_value)


def rms_sample_to_dbfs(sample, full_scale_value):
    return 20 * np.log10(sample / (_HALF_SQRT_2 * full_scale_value))
