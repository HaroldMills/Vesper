"""Module containing class `AddRecordingAudioFilesCommand`."""


from collections import defaultdict
from pathlib import Path, PureWindowsPath
import csv
import datetime
import logging
import random

from django.db import transaction

from vesper.archive_paths import archive_paths
from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import Recording, RecordingFile
from vesper.singleton.recording_manager import recording_manager
import vesper.command.command_utils as command_utils
import vesper.command.recording_utils as recording_utils


_CSV_FILE_PATH = (
    '/Users/harold/Desktop/NFC/Data/MPG Ranch/2012-2016 Recording File Lists/'
    '2016_Archive_results.csv')
"""
Path of CSV file containing information about MPG Ranch recording audio
files that Debbie Leick generated on her computer. This file is used
for testing purposes only.
"""


_SIMULATED_ERROR_PROBABILITY = 0
"""
Simulated recording file read error probability.

This is for simulating file read errors during testing. For normal
operation it should be zero.
"""


class AddRecordingAudioFilesCommand(Command):
    
    
    extension_name = 'add_recording_audio_files'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._station_names = frozenset(get('stations', args))
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._dry_run = get('dry_run', args)
 
        
    def execute(self, job_info):
        
        self._job_info = job_info
        self._logger = logging.getLogger()
        
        try:
            
            self._log_intro()
    
            # Get mapping from station names to nights to lists of
            # recording files sorted by start time.
            files = self._get_files(archive_paths.recording_dir_paths)
            # self._show_files(files)
        
            # self._compare_local_and_mpg_recording_files(files)
        
            # Get mapping from station names to nights to lists of
            # recordings sorted by start time.
            recordings = self._get_recordings()
        
            recording_files = self._assign_files_to_recordings(
                files, recordings)
        
            with transaction.atomic():
                self._add_recording_files(recording_files)
                
        except Exception as e:
            
            log = self._logger.error
            log('Command failed with an exception.')
            log('The exception message was:')
            log(f'    {str(e)}')
            log('The archive was not modified.')
            log('See below for exception traceback.')
            
            raise

        return True


    def _log_intro(self):
        
        log = self._logger.info
        
        if self._dry_run:
            log('This command is running in dry run mode. After this '
                'message it will log the same messages that it would '
                'during normal operation, often including messages '
                'indicating that it is modifying the archive database. '
                'However, it will not actually modify the database.')
 
        log('In this log, a recording in the archive database is '
            'described by its station name, start time, sample rate, '
            'number of channels, length in sample frames, and (in '
            'parentheses number of clips per channel, for example:')
        
        log('    Station 2020-02-10 01:23:45+00:00 24000.0 2 900000000 '
            '(100, 200)')
        
        log('A recording file in the archive database is described by its '
            'file number, file name, sample rate, number of channels, '
            'length in sample frames, and recording start offset in '
            'sample frames, for example:')
        
        log('    0 Station_20200210_012345.wav 24000.0 2 500000000 0')
        
        log('A recording file on disk is described before parsing by '
            'its file system path, for example:')
            
        log(r'    C:\Users\Nora\2020 Archive\Recordings'
            r'\Station_20200210_012345.wav')
        
        log('or after parsing by its file name, sample rate, number '
            'of channels, length in sample frames, and recording start '
            'offset in sample frames, for example:')
        
        log('    Station_20200210_012345.wav 24000.0 2 500000000 0')
        
        
    def _get_files(self, recordings_dir_paths):
        
        spec = {
            'name': 'MPG Ranch Recording File Parser',
            'arguments': {
                'station_name_aliases_preset': 'Station Name Aliases'
            }
        }
    
        file_parser = recording_utils.create_recording_file_parser(spec)
        
        # `files` maps station names to nights to lists of file info bunches.
        files = defaultdict(lambda: defaultdict(list))
        
        # Build mapping from station names to nights to lists of files.
        for dir_path in recordings_dir_paths:
            
            for file_path in dir_path.glob('**/*.wav'):
                
                try:
                    f = self._parse_file(file_path, file_parser)
    
                except Exception as e:
                    class_name = e.__class__.__name__
                    self._logger.warning(
                        f'Could not parse recording file "{file_path}". '
                        f'Attempt raised {class_name} exception with message: '
                        f'{str(e)} File will be ignored.')
                    
                else:
                    # file parse succeeded
                    
                    station_name = f.station.name
                    
                    if station_name in self._station_names:
                        
                        night = f.station.get_night(f.start_time)
                        
                        if night >= self._start_date and \
                                night <= self._end_date:
        
                            files[station_name][night].append(f)
                    
        # Sort file lists by start time.
        for station_files in files.values():
            for night_files in station_files.values():
                night_files.sort(key=lambda f: f.start_time)
                   
        return files
    
    
    def _parse_file(self, file_path, file_parser):
        
        if random.random() < _SIMULATED_ERROR_PROBABILITY:
            raise Exception('A simulated error occurred.')
        
        else:
            return file_parser.parse_file(str(file_path))
    
                    
    def _show_files(self, files):
        for station_name in sorted(files.keys()):
            print(station_name)
            station_files = files[station_name]
            for night in sorted(station_files.keys()):
                print(f'    {night}')
                night_files = station_files[night]
                for f in night_files:
                    print(
                        f'        "{f.path}",{f.num_channels},'
                        f'{f.sample_rate},{f.length}')
                    
                    
    def _compare_local_and_mpg_recording_files(self, local_files):
        
        local_files = self._create_local_files_dict(local_files)
        mpg_files = self._create_mpg_files_dict(_CSV_FILE_PATH)
        
        # self._show_recording_files_dict('local files', local_files)
        # self._show_recording_files_dict('MPG files', mpg_files)
        
        print()
        print('local - MPG:')
        self._show_differences(local_files, mpg_files)
        
        print()
        print('MPG - local:')
        self._show_differences(mpg_files, local_files)
        
        
    def _create_local_files_dict(self, files):
        
        result = {}
        
        for station_files in files.values():
            for night_files in station_files.values():
                for f in night_files:
                    file_name = Path(f.path).name
                    result[file_name] = (
                        f.num_channels, f.sample_rate, f.length)
                    
        return result
                    
                    
    def _create_mpg_files_dict(self, csv_file_path):
        
        result = {}
        
        with open(csv_file_path, newline='') as file_:
            
            reader = csv.reader(file_)
            
            for row in reader:
                
                file_name = PureWindowsPath(row[0]).name
                channel_num = int(row[1])
                sample_rate = float(row[2])
                length = int(row[3])
     
                result[file_name] = (channel_num, sample_rate, length)
                
        return result
            
            
    def _show_recording_files_dict(self, title, files):
        print(f'{title}:')
        for file_name in sorted(files.keys()):
            info = files[file_name]
            print(file_name, info)
            
    
    def _show_differences(self, a, b):
        for file_name in sorted(a.keys()):
            b_info = b.get(file_name)
            if b_info is None:
                print(f'{file_name} absent')
            elif b_info != a[file_name]:
                print(f'{file_name} info differs: {a[file_name]} {b_info}')
                
        
    def _get_recordings(self):
        
        # `recordings` maps station names to nights to lists of recordings.
        recordings = defaultdict(lambda: defaultdict(list))
        
        # Build mapping from station names to nights to lists of recordings.
        for r in Recording.objects.all().order_by(
                'station__name', 'start_time'):
            
            station_name = r.station.name
            
            if station_name in self._station_names:
                
                night = r.station.get_night(r.start_time)
                
                if night >= self._start_date and night <= self._end_date:
                    
                    recordings[r.station.name][night].append(r)
            
        # Sort recording lists by start time.
        for station_recordings in recordings.values():
            for night_recordings in station_recordings.values():
                night_recordings.sort(key=lambda r: r.start_time)
                
        return recordings
    
        
    def _assign_files_to_recordings(self, files, recordings):
        
        """Builds a mapping from recordings to lists of recording files."""
        
        # Start with a mapping from recordings to empty lists. We do this
        # to ensure there's an item in the mapping for every recording.
        recording_files = {}
        for station_name in sorted(recordings.keys()):
            station_recordings = recordings[station_name]
            for night in sorted(station_recordings.keys()):
                for r in station_recordings[night]:
                    recording_files[r] = []
        
        for station_name in sorted(files.keys()):
            
            station_files = files[station_name]
            
            for night in sorted(station_files.keys()):
                
                night_recordings = recordings[station_name][night]  
                night_files = station_files[night]
                
                for f in night_files:
                    
                    recording = self._assign_file_to_recording(
                        f, night_recordings)
                    
                    if recording is None:
                        # could not find recording for file
                        
                        self._log_unassigned_file(f)
                        
                    else:
                        # found recording for file
                        
                        recording_files[recording].append(f)
                        
        return recording_files
    
    
    def _assign_file_to_recording(self, file_, recordings):
        
        recording = None
        max_intersection = 0
        
        for r in recordings:
            
            # If recording has same start time as file, assign file to it,
            # regardless of any intersection considerations. (We encountered
            # a case where a file was misassigned to a recording with which
            # it overlapped more than it did with another recording that
            # shared its start time!)
            if r.start_time == file_.start_time:
                recording = r
                break
            
            intersection = self._get_intersection_duration(r, file_)
            
            if intersection > max_intersection:
                recording = r
                max_intersection = intersection
                
        return recording
    
            
    def _get_intersection_duration(self, r, file_):
        
        r_start = r.start_time
        r_end = r.end_time
        
        f_start = file_.start_time
        duration = datetime.timedelta(seconds=file_.length / file_.sample_rate)
        f_end = f_start + duration
        
        if f_end <= r_start or f_start >= r_end:
            return 0
        
        else:
            i_start = max(r_start, f_start)
            i_end = min(r_end, f_end)
            return (i_end - i_start).total_seconds()
        
        
    def _log_unassigned_file(self, f):
        file_string = self._get_file_string(f)
        self._logger.warning(
            f'Could not find recording for file {file_string}.')
        

    def _add_recording_files(self, recording_files):
        
        recordings = sorted(
            recording_files.keys(),
            key=lambda r: (r.station.name, r.start_time))
        
        for r in recordings:
            self._add_recording_files_aux(r, recording_files[r])
            
            
    def _add_recording_files_aux(self, recording, files):
        
        log_info = self._logger.info
        
        r = recording
        
        recording_string = self._get_recording_string(r)
        log_info(f'Processing recording {recording_string}...')
        
        db_files = list(r.files.all().order_by('file_num'))
        
        if len(db_files) != 0:
            # recording already has files in database
            
            if self._compare_files(db_files, files):
                log_info(
                    '    Recording has matching files in archive database '
                    'and on disk.')
                self._shorten_recording_length_if_needed(r, files)
                                
        else:
            # recording has no files in database
            
            if self._check_num_files(files) and \
                    self._check_file_sample_rates(r, files) and \
                    self._check_file_channels(r, files) and \
                    self._check_file_lengths(r, files):
                
                self._add_files_to_database(r, files)
                self._shorten_recording_length_if_needed(r, files)
                
                
    def _get_recording_string(self, r):
        clip_counts = self._get_recording_clip_counts(r)
        return (
            f'{r.station.name} {r.start_time} {r.sample_rate} '
            f'{r.num_channels} {r.length} {clip_counts}')
    
    
    def _get_recording_clip_counts(self, recording):
        channels = recording.channels.all().order_by('channel_num')
        return tuple(c.clips.count() for c in channels)

    
    def _compare_files(self, db_files, disk_files):
        
        if len(db_files) != 0 and len(disk_files) == 0:
            self._report_missing_disk_files(db_files)
            return False
            
        elif self._files_match(db_files, disk_files):
            return True
        
        else:
            self._report_files_mismatch(db_files, disk_files)
            return False
        
        
    def _report_missing_disk_files(self, db_files):
        
        self._logger.warning(
            '    Recording has files in the archive database, but not '
            'on disk.')
        self._log_database_files(db_files, self._logger.warning)
        self._log_no_action()
        
        
    def _log_database_files(self, db_files, log):
        log('    The database files are:')
        for f in db_files:
            log(
                f'        {f.file_num} {Path(f.path).name} '
                f'{f.sample_rate} {f.num_channels} {f.length} '
                f'{f.start_index}')


    def _log_no_action(self):
        self._logger.warning('    No action will be taken for this recording.')


    def _files_match(self, db_files, disk_files):
        
        if len(db_files) != len(disk_files):
            return False
        
        pairs = zip(db_files, disk_files)
        return all(self._files_match_aux(*p) for p in pairs)
                    

    def _files_match_aux(self, db_file, disk_file):
        
        db_name = Path(db_file.path).name
        disk_name = Path(disk_file.path).name
        
        return (
            db_name == disk_name and
            db_file.num_channels == disk_file.num_channels and
            db_file.length == disk_file.length and
            db_file.sample_rate == disk_file.sample_rate)
    
    
    def _report_files_mismatch(self, db_files, disk_files):
            
        log = self._logger.warning
        
        log(
            '    Recording already has files in the archive '
            'database, but they do not match the files on disk.')
        
        self._log_database_files(db_files, log)
        self._log_disk_files('The disk files are:', disk_files, log)
            
        self._log_no_action()


    def _log_disk_files(self, title, disk_files, log):
        log(f'    {title}')
        for f in disk_files:
            file_string = self._get_file_string(f)
            log(f'        {file_string}')
            

    def _get_file_string(self, f):
        return (
            f'{Path(f.path).name} {f.start_time} {f.sample_rate} '
            f'{f.num_channels} {f.length}')
    
    
    def _shorten_recording_length_if_needed(self, recording, files):
        
        r_length = recording.length
        f_length = sum(f.length for f in files)
        
        sample_rate = recording.sample_rate
        two_seconds = 2 * sample_rate
        
        if r_length - f_length == two_seconds:
            # Recording length specified in database is exactly two
            # seconds longer than total length of files. The
            # `populate_archive` script that was used to populate
            # web archives from desktop archives added two seconds
            # to recording durations to try to ensure that the times
            # of clips created by the original Old Bird detectors
            # were within the time span of the recording. We remove
            # this padding since it is not needed.
            
            self._logger.info(
                '    Reducing recording duration by two seconds to '
                'remove unneeded padding added by populate_archive script.')
        
            recording.length = f_length
             
            span = (f_length - 1) / sample_rate
            recording.end_time = \
                recording.start_time + datetime.timedelta(seconds=span)
                     
            if not self._dry_run:
                recording.save()
    
    
    def _check_num_files(self, files):
        
        if len(files) == 0:
            self._logger.warning(
                '    No files were found either in the archive database '
                'or on disk for this recording.')
            return False
        
        else:
            return True
        
        
    def _check_file_sample_rates(self, recording, files):
        
        sample_rate = recording.sample_rate
        
        for f in files:
            
            if f.sample_rate != sample_rate:
                
                self._logger.warning(
                    '    The sample rate of one or more of this '
                    "recording's files does not match that of the "
                    'recording.')
                
                self._log_disk_files(
                    'The files are:', files, self._logger.warning)
                
                self._log_no_action()
                
                return False
            
        # If we get here, the sample rates of all of the files
        # matched the sample rate of the recording.
        return True
    
    
    def _check_file_channels(self, recording, files):
        
        num_channels = recording.num_channels
        
        for f in files:
            
            if f.num_channels != num_channels:
                
                self._logger.warning(
                    '    The number of channels of one or more of this '
                    "recording's files does not match that of the "
                    'recording.')
                    
                self._log_disk_files(
                    'The files are:', files, self._logger.warning)
                
                self._log_no_action()
                
                return False
            
        # If we get here, the number of channels of all of the files
        # matched the number of channels of the recording.
        return True
    
    
    def _check_file_lengths(self, recording, files):
        
        r_length = recording.length
        f_length = sum(f.length for f in files)
        
        two_seconds = 2 * recording.sample_rate
        
        # The `populate_archive` script that was used to populate
        # web archives from desktop archives added two seconds
        # to recording durations to try to ensure that the times
        # of clips created by the original Old Bird detectors
        # were within the time span of the recording. We take
        # that into consideration in the following comparison.
        if r_length != f_length and r_length - f_length != two_seconds:
            # recording and file lengths don't match
            
            self._logger.warning(
                "    The total length of this recording's files "
                'does not match that of the recording.')
            
            self._log_disk_files('The files are:', files, self._logger.warning)
            
            self._log_no_action()
            
            return False
        
        else:
            # recording and file lengths match
            
            return True
    
    
    def _add_files_to_database(self, recording, files):
        
        self._log_disk_files(
            'Adding files to archive database:', files, self._logger.info)
        
        start_index = 0         
        
        for file_num, f in enumerate(files):
            
            # We store all paths in the archive database as POSIX
            # paths, even on Windows, for portability, since Python's
            # `pathlib` module recognizes the slash as a path separator
            # on all platforms, but not the backslash.
            path = self._get_relative_path(f.path).as_posix()
            
            file_ = RecordingFile(
                recording=recording,
                file_num=file_num,
                start_index=start_index,
                length=f.length,
                path=path)
            
            if not self._dry_run:
                file_.save()
            
            start_index += f.length
            
            
    def _get_relative_path(self, abs_path):
        
        rm = recording_manager
        
        try:
            _, rel_path = rm.get_relative_recording_file_path(abs_path)
            
        except ValueError:
            
            dir_paths = rm.recording_dir_paths
            
            if len(dir_paths) == 1:
                s = f'the recording directory "{dir_paths[0]}"'
            else:
                path_list = str(list(dir_paths))
                s = f'any of the recording directories {path_list}'
                
            raise CommandExecutionError(
                f'Recording file "{abs_path}" is not in {s}.')
                        
        return rel_path
