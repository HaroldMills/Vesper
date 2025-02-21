from datetime import timedelta as TimeDelta
from pathlib import Path
import collections
import wave

import numpy as np

from vesper.recorder.processor import Processor
from vesper.recorder.settings import Settings
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


_DEFAULT_RECORDING_DIR_PATH = 'Recordings'

_RECORDING_SUBDIRS = (
    'Recording Name', 'Station Name', 'Year', 'Month', 'Day', 'Date',
    'Year-Month', 'Month-Day')
_DEFAULT_RECORDING_SUBDIRS = ('Recording Name',)

_FILE_SORT_TIMES = ('Recording Start Time', 'File Start Time')
_DEFAULT_FILE_SORT_TIME = 'Recording Start Time'

_FILE_SORT_PERIODS = ('UTC Day', 'Local Day', 'Local Night')
_DEFAULT_FILE_SORT_PERIOD = 'UTC Day'

_12_HOURS = TimeDelta(hours=12)

_FILE_SORT_DATE_FORMATS = {
    'Year': '%Y',
    'Month': '%m',
    'Day': '%d',
    'Date': '%Y-%m-%d',
    'Year-Month': '%Y-%m',
    'Month-Day': '%m-%d'
}

_DEFAULT_MAX_AUDIO_FILE_DURATION = 3600     # seconds

_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav.in_progress'


class AudioFileWriter(Processor):
    
    
    type_name = 'Audio File Writer'


    @staticmethod
    def parse_settings(settings):
        return _parse_settings(settings)
    

    def __init__(self, name, settings, context, input_info):
        
        super().__init__(name, settings, context, input_info)

        self._channel_count = input_info.channel_count
        self._sample_rate = input_info.sample_rate
        
        self._recording_dir_path = settings.recording_dir_path
        self._recording_subdirs = settings.recording_subdirs
        self._file_sort_time = settings.file_sort_time
        self._file_sort_period = settings.file_sort_period
        self._max_audio_file_duration = settings.max_audio_file_duration

        # Create audio file namer.
        self._audio_file_namer = _AudioFileNamer(
            context.station.name, _AUDIO_FILE_NAME_EXTENSION)
        
        # Get audio file sample frame size in bytes.
        self._frame_size = self._channel_count * _SAMPLE_SIZE // 8
        
        # Get max audio file size in sample frames.
        self._max_file_frame_count = \
            int(round(self._max_audio_file_duration * self._sample_rate))
                    
        
    @property
    def recording_dir_path(self):
        return self._recording_dir_path
    

    @property
    def recording_subdirs(self):
        return self._recording_subdirs
    

    @property
    def file_sort_time(self):
        return self._file_sort_time
    

    @property
    def file_sort_period(self):
        return self._file_sort_period
    

    @property
    def max_audio_file_duration(self):
        return self._max_audio_file_duration
    

    def _start(self):
        
        self._recording_start_time = time_utils.get_utc_now()

        station = self.context.station
        self._audio_file_sorter = _AudioFileSorter(
            station.name, station.time_zone, self._recording_start_time,
            self._recording_subdirs, self._file_sort_time,
            self._file_sort_period)
        
        self._audio_file = None
        self._audio_file_path = None

        self._total_frame_count = 0
        
    
    def _process(self, input_item, finished):
        
        # TODO: Consider using (and reusing) more pre-allocated buffers
        # in the following, to reduce memory churn.
        # Transpose, scale, round, and clip samples, convert to int16,
        # and get resulting bytes.
        samples = input_item.samples[:, :input_item.frame_count].transpose()
        samples = 32768 * samples
        np.rint(samples, out=samples)
        np.clip(samples, -32768, 32767, out=samples)
        samples = np.array(samples, dtype='int16').tobytes()
            
        remaining_frame_count = input_item.frame_count
        buffer_index = 0
        output_items = []

        while remaining_frame_count != 0:
            
            if self._audio_file is None:
                self._audio_file, self._audio_file_path = \
                    self._open_audio_file()
                self._file_frame_count = 0
        
            frame_count = min(
                remaining_frame_count,
                self._max_file_frame_count - self._file_frame_count)
                
            byte_count = frame_count * self._frame_size
            
            self._audio_file.writeframes(
                samples[buffer_index:buffer_index + byte_count])
            
            remaining_frame_count -= frame_count
            self._file_frame_count += frame_count
            self._total_frame_count += frame_count
            buffer_index += byte_count
            
            if self._file_frame_count == self._max_file_frame_count:
                output_item = self._complete_audio_file()
                output_items.append(output_item)

        if finished and self._audio_file is not None:
            # all input has arrived and there's an open audio file
            # that is not yet full

            output_item = self._complete_audio_file()
            output_items.append(output_item)

        return output_items
    
    
    def _open_audio_file(self):
        
        # Get audio file name.
        duration = self._total_frame_count / self._sample_rate
        time_delta = TimeDelta(seconds=duration)
        file_start_time = self._recording_start_time + time_delta
        file_name = self._audio_file_namer.get_file_name(file_start_time)

        # Get audio file path relative to recording directory.
        dir_path = self._audio_file_sorter.get_dir_path(file_start_time)
        rel_file_path = dir_path / file_name
        
        # Get absolute audio file path.
        abs_file_path = self._recording_dir_path / rel_file_path

        # Create ancestor directories for audio file as needed.
        dir_path = abs_file_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        # Create audio file.
        file = wave.open(str(abs_file_path), 'wb')
        file.setnchannels(self._channel_count)
        file.setframerate(self._sample_rate)
        file.setsampwidth(_SAMPLE_SIZE // 8)
        
        return file, rel_file_path
    

    def _complete_audio_file(self):

        self._audio_file.close()

        # Get relative path of completed audio file, dropping
        # ".in_progress" extension from incomplete audio file path.
        completed_audio_file_path = \
            self._audio_file_path.parent / self._audio_file_path.stem

        # Rename completed audio file.
        from_path = self._recording_dir_path / self._audio_file_path
        to_path = self._recording_dir_path / completed_audio_file_path
        from_path.rename(to_path)

        self._audio_file = None
        self._audio_file_path = None

        return (self._recording_dir_path, completed_audio_file_path)


    def get_status_tables(self):

        recording_dir_path = self.recording_dir_path.absolute()

        rows = (
            ('Recording Directory', recording_dir_path),
            ('Recording Subdirectories', self._recording_subdirs),
            ('File Sort Time', self._file_sort_time),
            ('File Sort Period', self._file_sort_period),
            ('Max Audio File Duration (seconds)', self.max_audio_file_duration)
        )

        table = StatusTable(self.name, rows)

        return [table]
    

def _parse_settings(settings):
   return Bunch(
        recording_dir_path=_parse_recording_dir_path(settings),
        recording_subdirs=_parse_recording_subdirs(settings),
        file_sort_time=_parse_file_sort_time(settings),
        file_sort_period=_parse_file_sort_period(settings),
        max_audio_file_duration=_parse_max_audio_file_duration(settings))


def _parse_recording_dir_path(settings):
    path = Path(settings.get(
        'recording_dir_path', _DEFAULT_RECORDING_DIR_PATH)).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _parse_recording_subdirs(settings):

    codes = settings.get('recording_subdirs', _DEFAULT_RECORDING_SUBDIRS)

    if not isinstance(codes, collections.abc.Sequence):
        values = [f'"{v}"' for v in _RECORDING_SUBDIRS]
        values_text = '{' + ', '.join(values) + '}'
        raise ValueError(
            f'Audio file writer recording subdirectories setting must '
            f'be a sequence of subdirectory codes, with each code in '
            f'{values_text}.')
    
    for code in codes:
        Settings.check_enum_value(
            code, _RECORDING_SUBDIRS,
            'audio file writer recording subdirectory')
    
    return tuple(codes)


def _parse_file_sort_time(settings):
    time = settings.get('file_sort_time', _DEFAULT_FILE_SORT_TIME)
    Settings.check_enum_value(
        time, _FILE_SORT_TIMES, 'audio file writer file sort time')
    return time


def _parse_file_sort_period(settings):
    period = settings.get('file_sort_period', _DEFAULT_FILE_SORT_PERIOD)
    Settings.check_enum_value(
        period, _FILE_SORT_PERIODS, 'audio file writer file sort period')
    return period


def _parse_max_audio_file_duration(settings):
    return settings.get(
        'max_audio_file_duration', _DEFAULT_MAX_AUDIO_FILE_DURATION)


class _AudioFileSorter:


    def __init__(
            self, station_name, station_time_zone, recording_start_time,
            recording_subdirs, file_sort_time, file_sort_period):

        self._station_name = station_name
        self._station_time_zone = station_time_zone
        self._recording_start_time = recording_start_time
        self._recording_subdirs = recording_subdirs
        self._file_sort_time = file_sort_time
        self._file_sort_period = file_sort_period

        self._recording_name = self._get_recording_name()


    def _get_recording_name(self):
        time = self._recording_start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self._station_name}_{time}_Z'

    
    def get_dir_path(self, file_start_time):

        sort_date = self._get_sort_date(file_start_time)

        dir_names = [
            self._get_dir_name(c, sort_date)
            for c in self._recording_subdirs]
        
        return Path(*dir_names)


    def _get_sort_date(self, file_start_time):
        
        # Get sort time.
        if self._file_sort_time == 'Recording Start Time':
            sort_time = self._recording_start_time
        else:
            sort_time = file_start_time

        # Get sort date.
        if self._file_sort_period == 'UTC Day':
            return sort_time.date()
        else:
            local_time = sort_time.astimezone(self._station_time_zone)
            if self._file_sort_period == 'Local Night':
                local_time -= _12_HOURS
            return local_time.date()
        

    def _get_dir_name(self, code, sort_date):

        match code:

            case 'Recording Name':
                return self._recording_name

            case 'Station Name':
                return self._station_name
            
            case _:
                format = _FILE_SORT_DATE_FORMATS[code]
                return sort_date.strftime(format)


class _AudioFileNamer:
    
    
    def __init__(self, station_name, file_name_extension):
        self._station_name = station_name
        self._file_name_extension = file_name_extension
        
        
    def get_file_name(self, file_start_time):
        time = file_start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self._station_name}_{time}_Z{self._file_name_extension}'
