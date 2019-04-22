"""Module containing the `VesperRecorder` class."""


from http.server import HTTPServer, BaseHTTPRequestHandler
from logging import FileHandler, Formatter
from threading import Thread
import datetime
import logging
import math
import os
import wave

import pyaudio
import pytz

from vesper.util.audio_recorder import AudioRecorder, AudioRecorderListener
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule
import vesper.util.yaml_utils as yaml_utils


# TODO: Review threads involved in recording (schedule, recorder, and server),
# clarify their responsibilities, and improve error handling and shutdown.
# Implement configuration updates and remote logging and control. How does
# recording relate to Vesper job system (as of this writing it's completely
# independent, but perhaps it should not be)? How does it relate to other
# processing, like detection and classification, that we would like to be
# able to schedule?


_HOME_DIR_VAR_NAME = 'VESPER_RECORDER_HOME'
_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_CONFIG_FILE_NAME = 'Vesper Recorder Config.yaml'

_AUDIO_FILE_NAME_EXTENSION = '.wav'
_AUDIO_FILE_HEADER_SIZE = 44                # bytes, size of .wav file header

_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_LATITUDE = None
_DEFAULT_LONGITUDE = None
_DEFAULT_TIME_ZONE = 'UTC'
_DEFAULT_NUM_CHANNELS = 1
_DEFAULT_SAMPLE_RATE = 22050
_DEFAULT_BUFFER_SIZE = .05
_DEFAULT_TOTAL_BUFFER_SIZE = 60
_DEFAULT_RECORDINGS_DIR_PATH = 'Recordings'
_DEFAULT_MAX_AUDIO_FILE_SIZE = 2**31        # bytes
_DEFAULT_PORT_NUM = 8001


_logger = logging.getLogger(__name__)


class VesperRecorder:
    
    """Records audio to .wav files according to a schedule."""
    
    
    VERSION_NUMBER = '0.2.0a0'


    @staticmethod
    def get_input_devices():
        return AudioRecorder.get_input_devices()
    
    
    @staticmethod
    def create_and_start_recorder(message):
        return _create_and_start_recorder(message)
    
    
    def __init__(self, config):
        self._config = config
                
        
    def start(self):
        
        c = self._config
        
        self._recorder = AudioRecorder(
            c.input_device_index, c.num_channels, c.sample_rate, c.buffer_size,
            c.total_buffer_size, c.schedule)
        self._recorder.add_listener(_Logger())
        self._recorder.add_listener(_AudioFileWriter(
            c.station_name, c.recordings_dir_path, c.max_audio_file_size))
         
        server = _HttpServer(
            c.port_num, c.station_name, c.lat, c.lon, c.time_zone,
            self._recorder, c.recordings_dir_path, c.max_audio_file_size)
        Thread(target=server.serve_forever, daemon=True).start()

        self._recorder.start()
         

    def wait(self, timeout=None):
        self._recorder.wait(timeout)
        
        
    def stop(self):
        self._recorder.stop()
        
        
def _create_and_start_recorder(message):
    
    home_dir_path = os.environ.get(_HOME_DIR_VAR_NAME)
     
    # Check that home directory path environment variable is set.
    if home_dir_path is None:
        _logger.error(
            'Required {} environment variable is not set.'.format(
                _HOME_DIR_VAR_NAME))
        return None
         
    # Check that home directory exists.
    if not os.path.exists(home_dir_path):
        _logger.error(
            'Recorder home directory "{}" does not exist.'.format(
                home_dir_path))
        return None
    
    # Now that we know that we have a home directory, and hence a place
    # for a log file, add file logging.
    _add_file_logging(home_dir_path)
    
    _logger.info(message)
    
    _logger.info(
        'Recorder version number is {}.'.format(VesperRecorder.VERSION_NUMBER))
    
    config_file_path = os.path.join(home_dir_path, _CONFIG_FILE_NAME)
        
    # Check that configuration file exists.
    if not os.path.exists(config_file_path):
        _logger.error(
            'Recorder configuration file "{}" does not exist.'.format(
                config_file_path))
        return None
        
    # Parse configuration file.
    try:
        config = _parse_config_file(
            config_file_path, home_dir_path)
    except Exception as e:
        _logger.error((
            'Could not parse recorder configuration file "{}". Error '
            'message was: {}').format(config_file_path, str(e)))
        return None
    
    _logger.info(
        'Starting recorder with HTTP server at port {}.'.format(
            config.port_num))
    
    # Create recorder.
    try:
        recorder = VesperRecorder(config)
    except Exception as e:
        _logger.error(
            'Could not create recorder. Error message was: {}'.format(str(e)))
        return None
           
    # Start recorder. 
    try:
        recorder.start()
    except Exception as e:
        _logger.error(
            'Could not start recorder. Error message was: {}'.format(str(e)))
        return None
    
    # Phew. We made it!
    return recorder
        

def _add_file_logging(home_dir_path):
    
    # Create handler that appends messages to log file.
    log_file_path = os.path.join(home_dir_path, _LOG_FILE_NAME)
    handler = FileHandler(log_file_path)
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to root logger.
    logger = logging.getLogger()
    logger.addHandler(handler)
        
        
def _parse_config_file(file_path, home_dir_path):
    
    with open(file_path) as f:
        config = yaml_utils.load(f)
        
    station_name = config.get('station', _DEFAULT_STATION_NAME)
    
    lat = config.get('latitude', _DEFAULT_LATITUDE)
    if lat is not None:
        lat = float(lat)
        
    lon = config.get('longitude', _DEFAULT_LONGITUDE)
    if lon is not None:
        lon = float(lon)
        
    time_zone = pytz.timezone(config.get('time_zone', _DEFAULT_TIME_ZONE))
        
    input_device_index = _get_input_device_index(config.get('input_device'))
    num_channels = int(config.get('num_channels', _DEFAULT_NUM_CHANNELS))
    sample_rate = int(config.get('sample_rate', _DEFAULT_SAMPLE_RATE))
    buffer_size = float(config.get('buffer_size', _DEFAULT_BUFFER_SIZE))
    total_buffer_size = \
        float(config.get('total_buffer_size', _DEFAULT_TOTAL_BUFFER_SIZE))
    
    schedule_dict = config.get('schedule', {})
    schedule = Schedule.compile_dict(
        schedule_dict, lat=lat, lon=lon, time_zone=time_zone)
    
    recordings_dir_path = config.get(
        'recordings_dir_path', _DEFAULT_RECORDINGS_DIR_PATH)
    if not os.path.isabs(recordings_dir_path):
        recordings_dir_path = os.path.join(home_dir_path, recordings_dir_path)
        
    max_audio_file_size = config.get(
        'max_audio_file_size', _DEFAULT_MAX_AUDIO_FILE_SIZE)
    
    port_num = int(config.get('port_num', _DEFAULT_PORT_NUM))
    
    return Bunch(
        station_name=station_name,
        lat=lat,
        lon=lon,
        time_zone=time_zone,
        input_device_index=input_device_index,
        num_channels=num_channels,
        sample_rate=sample_rate,
        buffer_size=buffer_size,
        total_buffer_size=total_buffer_size,
        schedule=schedule,
        recordings_dir_path=recordings_dir_path,
        max_audio_file_size=max_audio_file_size,
        port_num=port_num)
    
    
def _get_input_device_index(device):
    
    if device is None:
        return _get_default_input_device_index()

    else:
        
        try:
            return int(device)
        
        except ValueError:
            return _get_input_device_index_from_device_name(device)
    
    
def _get_default_input_device_index():
    
    pa = pyaudio.PyAudio()
    
    try:
        info = pa.get_default_input_device_info()
        
    except IOError:
        raise ValueError('Could not get default input device info.')
    
    finally:
        pa.terminate()
        
    return info['index']
    

def _get_input_device_index_from_device_name(name):
    
    pa = pyaudio.PyAudio()
    
    # Get all device infos.
    num_devices = pa.get_device_count()
    infos = [pa.get_device_info_by_index(i) for i in range(num_devices)]
    
    pa.terminate()
    
    # Remove non-input device infos.
    infos = [i for i in infos if i['maxInputChannels'] != 0]
    
    if len(infos) == 0:
        raise ValueError('No input devices were found.')
    
    # Find infos for devices whose names include `name`.
    infos = [i for i in infos if name in i['name']]
    
    if len(infos) == 0:
        raise ValueError(
            'No input device name includes "{}".'.format(name))
        
    elif len(infos) > 1:
        raise ValueError(
            'More than one input device name includes "{}".'.format(name))
        
    else:
        return infos[0]['index']
    
    
class _Logger(AudioRecorderListener):
    
    
    def __init__(self):
        super().__init__()
        self._pyaudio_overflow_buffer_count = 0
        self._num_recorder_overflow_frames = 0
        
        
    def recording_started(self, recorder, time):
        self._sample_rate = recorder.sample_rate
        _logger.info('Started recording.')
        
        
    def input_arrived(
            self, recorder, time, samples, num_frames, pyaudio_overflow):
        
        self._log_pyaudio_overflow_if_needed(pyaudio_overflow)
        self._log_recorder_overflow_if_needed(False)
            
            
    def _log_pyaudio_overflow_if_needed(self, overflow):
        
        if overflow:
            
            if self._pyaudio_overflow_buffer_count == 0:
                # overflow has just started
                
                _logger.error(
                    'PyAudio input overflow: PyAudio has reported that '
                    'an unspecified number of input samples were dropped '
                    'before or during the current buffer. A second message '
                    'will be logged later indicating the number of '
                    'consecutive buffers for which this error occurred.')
                
            self._pyaudio_overflow_buffer_count += 1
            
        else:
            
            if self._pyaudio_overflow_buffer_count > 0:
                # overflow has just ended
                
                if self._pyaudio_overflow_buffer_count == 1:
                    
                    _logger.error(
                        'PyAudio input overflow: Overflow was reported for '
                        'one buffer.')
                    
                else:
                    
                    _logger.error((
                        'PyAudio input overflow: Overflow was reported for '
                        '{} consecutive buffers.').format(
                            self._pyaudio_overflow_buffer_count))
            
                self._pyaudio_overflow_buffer_count = 0
            

    def _log_recorder_overflow_if_needed(self, overflow, num_frames=0):
        
        if overflow:
            
            if self._num_recorder_overflow_frames == 0:
                # overflow has just started
                
                _logger.error(
                    'Recorder input overflow: The recorder has run out of '
                    'buffers for arriving input samples. It will substitute '
                    'zero samples until buffers become available, and then '
                    'log another message to report the duration of the lost '
                    'samples.')
                
            self._num_recorder_overflow_frames += num_frames
            
        else:
            
            if self._num_recorder_overflow_frames > 0:
                # overflow has just ended
                
                _logger.error((
                    'Recorder input overflow: {:.3f} seconds of zero samples '
                    'were substituted for lost input samples.').format(
                        self._num_recorder_overflow_frames / self._sample_rate)
                )
                    
                self._num_recorder_overflow_frames = 0
                    
        
    def input_overflowed(self, recorder, time, num_frames, pyaudio_overflow):
        self._log_pyaudio_overflow_if_needed(pyaudio_overflow)
        self._log_recorder_overflow_if_needed(True, num_frames)
        
        
    def recording_stopped(self, recorder, time):
        self._log_pyaudio_overflow_if_needed(False)
        self._log_recorder_overflow_if_needed(False)
        _logger.info('Stopped recording.')

    
class _AudioFileWriter(AudioRecorderListener):
    
    
    def __init__(self, station_name, recordings_dir_path, max_file_size):
        
        super().__init__()
        
        self._station_name = station_name
        self._recordings_dir_path = recordings_dir_path
        self._max_file_size = max_file_size
        
        # Create recordings directory if needed.
        os.makedirs(self._recordings_dir_path, exist_ok=True)
        
        
    def recording_starting(self, recorder, time):
        
        self._num_channels = recorder.num_channels
        self._sample_rate = recorder.sample_rate
        self._sample_size = recorder.sample_size
        self._frame_size = self._num_channels * self._sample_size
        self._zeros = bytearray(recorder.frames_per_buffer * self._frame_size)
        
        max_num_audio_bytes = self._max_file_size - _AUDIO_FILE_HEADER_SIZE
        self._max_num_file_frames = \
            int(math.floor(max_num_audio_bytes / self._frame_size))
                    
        self._file_namer = _AudioFileNamer(
            self._station_name, _AUDIO_FILE_NAME_EXTENSION)
        
        self._file = None
        
    
    def input_arrived(
            self, recorder, time, samples, num_frames, pyaudio_overflow):
        self._write_samples(time, samples, num_frames)
        
        
    def _write_samples(self, time, samples, num_frames):
        
        num_frames_remaining = num_frames
        buffer_index = 0
        
        while num_frames_remaining != 0:
            
            if self._file is None:
                self._file = self._open_audio_file(time)
                self._num_file_frames = 0
        
            num_frames = min(
                num_frames_remaining,
                self._max_num_file_frames - self._num_file_frames)
                
            num_bytes = num_frames * self._frame_size
            
            # TODO: We assume here that the sample bytes are in
            # little-endian order, but perhaps we shouldn't.
            self._file.writeframes(
                samples[buffer_index:buffer_index + num_bytes])
            
            num_frames_remaining -= num_frames
            self._num_file_frames += num_frames
            buffer_index += num_bytes
            
            if self._num_file_frames == self._max_num_file_frames:
                self._file.close()
                self._file = None
    
    
    def input_overflowed(self, recorder, time, num_frames, pyaudio_overflow):
        self._write_samples(time, self._zeros, num_frames)
    
        
    def _open_audio_file(self, time):
        
        file_name = self._file_namer.create_file_name(time)
        file_path = os.path.join(self._recordings_dir_path, file_name)
        
        file_ = wave.open(file_path, 'wb')
        file_.setnchannels(self._num_channels)
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
        return '{}_{}_Z{}'.format(
            self.station_name, time, self.file_name_extension)
        
        
class _HttpServer(HTTPServer):
    
    
    def __init__(
            self, port_num, station_name, lat, lon, time_zone, recorder,
            recordings_dir_path, max_audio_file_size):
        
        address = ('', port_num)
        super().__init__(address, _HttpRequestHandler)
        
        self._recording_data = Bunch(
            station_name=station_name,
            lat=lat,
            lon=lon,
            time_zone=time_zone,
            recorder=recorder,
            recordings_dir_path=recordings_dir_path,
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
        now = datetime.datetime.now(tz=pytz.utc)
                
        status_table = self._create_status_table(data, recorder, now)
        station_table = self._create_station_table(data)
        devices = recorder.get_input_devices()
        devices_table = self._create_devices_table(devices)
        input_table = self._create_input_table(devices, recorder)
        output_table = self._create_output_table(data)
        recordings_table = self._create_recordings_table(
            recorder.schedule, data.time_zone, now)
        
        body = _PAGE.format(
            _CSS, VesperRecorder.VERSION_NUMBER, status_table, station_table,
            devices_table, input_table, output_table, recordings_table)
        
        return body.encode()
    
    
    def _create_status_table(self, data, recorder, now):
        
        time_zone = data.time_zone
        
        time = _format_datetime(now, time_zone)
        recording = 'Yes' if recorder.recording else 'No'
        
        interval = self._get_status_schedule_interval(recorder.schedule, now)
        
        if interval is None:
            prefix = 'Next'
            start_time = 'None'
            end_time = 'None'
        else:
            start_time = _format_datetime(interval.start, time_zone)
            end_time = _format_datetime(interval.end, time_zone)
            prefix = 'Current' if interval.start <= now else 'Next'
            
        rows = (
            ('Time', time),
            ('Recording', recording),
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
            header = ('Index', 'Name', 'Number of Channels')
            table = _create_table(rows, header)
            if selected_device_index < len(devices):
                table += '<p>* Selected input device.</p>'
            return table

    
    def _create_devices_table_row(self, device, selected_device_index):
        prefix = '*' if device.index == selected_device_index else ''
        return (
            prefix + str(device.index), device.name, device.num_input_channels)
    
    
    def _create_input_table(self, devices, recorder):
        
        device_index = recorder.input_device_index
        
        if device_index < len(devices):
            device_name = devices[device_index].name
        else:
            message = 'There is no input device with index {}.'
            device_name = message.format(device_index)
            
        rows = (
            ('Device Index', device_index),
            ('Device Name', device_name),
            ('Number of Channels', recorder.num_channels),
            ('Sample Rate (Hz)', recorder.sample_rate),
            ('Buffer Size (seconds)', recorder.buffer_size)
        )
        return _create_table(rows)
    
    
    def _create_output_table(self, data):
        recordings_dir_path = os.path.abspath(data.recordings_dir_path)
        rows = (
            ('Recordings Directory', recordings_dir_path),
            ('Max Audio File Size (bytes)', data.max_audio_file_size)
        )
        return _create_table(rows)


    def _create_recordings_table(self, schedule, time_zone, now):
        rows = [
            self._create_recordings_table_row(index, interval, time_zone, now)
            for index, interval in enumerate(schedule.get_intervals())]
        header = ('Index', 'Start Time', 'End Time', 'Status')
        return _create_table(rows, header)
    
    
    def _create_recordings_table_row(self, index, interval, time_zone, now):
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
    return '    <t{}>{}</t{}>\n'.format(tag_letter, item, tag_letter)
