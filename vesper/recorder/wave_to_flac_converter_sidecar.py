# Sidecar that converts WAVE files to FLAC files.
#
# This sidecar searches for WAVE files to convert to FLAC files in
# specified recording directories. It utilizes a different thread for
# each recording directory (see the `_ConvertThread` class below). A
# directory's thread runs in a loop, checking the directory for WAVE
# files, converting any found, and then sleeping for a while. The thread
# converts a WAVE file by running the third-party `flac` program in a
# subprocess. The created FLAC file includes a seek table that can be
# used to accelerate audio sample read operations.
#
# `flac` is an open source program produced by xiph.org. Documentation
# for the program is at https://xiph.org/flac/documentation_tools_flac.html.
# Source code for the program is at https://github.com/xiph/flac.
#
# We use the `flac` program's `-S` option to include seek tables in the
# FLAC files it writes. As of `flac` version 1.5.0, the `-S` option has a
# couple of limitations that affect the operation of this sidecar, and that
# we document here.
#
# First, if you specify a `flac` command line option of the form `-S #s`,
# which this sidecar does and which specifies that seek points should be
# spaced `#` seconds apart, the program quietly replaces a separation
# smaller than .5 seconds with .5 seconds. This happens in the
# `grabbag__seektable_convert_specification_to_template` function in file
# `flac/src/share/grabbag/seektable.c` of the `flac` source code.
#
# Second, if you specify to the `flac` program that it should create a seek
# table with more than 32768 points, whether directly with an option of the
# form `-S #x` or indirectly with an option of the form `-S #s`, the program
# quietly reduces the number of seek points to 32768. This happens in the
# `FLAC__metadata_object_seektable_template_append_spaced_points_by_samples`
# function in file `flac/src/libFLAC/metadata_object.c` of the `flac` source
# code.


from pathlib import Path
from threading import Thread
import logging
import multiprocessing as mp
import subprocess
import threading

from vesper.recorder.settings import Settings
from vesper.recorder.sidecar import Sidecar
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


_DEFAULT_SEARCH_RECURSIVELY = True
_DEFAULT_SEEK_POINT_SPACING = 1             # seconds
_DEFAULT_SLEEP_PERIOD = 60                  # seconds

_FLAC_FILE_NAME_EXTENSION = '.flac'
_IN_PROGRESS_FILE_NAME_EXTENSION = _FLAC_FILE_NAME_EXTENSION + '.in_progress'


# Example sidecar settings:
#
#     default_search_recursively: true
#     default_seek_point_spacing: 1
#     default_sleep_period: 60
#     recording_dirs:
#         - dir_path: Recordings
#           search_recursively: false
#           seek_point_spacing: .5
#           sleep_period: 30


class WaveToFlacConverterSidecar(Sidecar):


    type_name = 'WAVE to FLAC Converter'


    @staticmethod
    def parse_settings(settings):

        s = settings

        default_search_recursively = s.get(
            'default_search_recursively', _DEFAULT_SEARCH_RECURSIVELY)

        default_seek_point_spacing = float(settings.get(
            'default_seek_point_spacing', _DEFAULT_SEEK_POINT_SPACING))

        default_sleep_period = float(s.get(
            'default_sleep_period', _DEFAULT_SLEEP_PERIOD))
        

        def parse_recording_dir_settings(mapping):

            s = Settings(mapping)

            dir_path = _get_absolute_path(
                Path(s.get_required('dir_path', 'recording directory')))

            search_recursively = s.get(
                'search_recursively', default_search_recursively)
            
            seek_point_spacing = float(s.get(
                'seek_point_spacing', default_seek_point_spacing))
            
            sleep_period = float(s.get('sleep_period', default_sleep_period))
            
            return Bunch(
                dir_path=dir_path,
                search_recursively=search_recursively,
                seek_point_spacing=seek_point_spacing,
                sleep_period=sleep_period)


        recording_dirs = [
            parse_recording_dir_settings(s)
            for s in settings.get('recording_dirs', [])]

        return Bunch(
            default_search_recursively=default_search_recursively,
            default_seek_point_spacing=default_seek_point_spacing,
            default_sleep_period=default_sleep_period,
            recording_dirs=recording_dirs)


    def __init__(self, name, settings, context):
        super().__init__(name, settings, context)
        self._stop_event = mp.Event()


    def _run(self):
            
        # Create threads.
        threads = [_ConvertThread(s) for s in self._settings.recording_dirs]

        # Start threads.
        for thread in threads:
            thread.start()
        
        # Wait for stop event.
        self._stop_event.wait()

        # Tell threads to stop.
        for thread in threads:
            thread.stop()

        # Wait for threads to finish.
        for thread in threads:
            thread.join()


    def stop(self):
        self._stop_event.set()


    def get_status_tables(self):
        main_table = self._get_main_status_table()
        dir_tables = self._get_recording_dir_status_tables()
        return [main_table] + dir_tables


    def _get_main_status_table(self):

        s = self.settings

        rows = (
            ('Default Search Recursively', s.default_search_recursively),
            ('Default Seek Point Spacing (seconds)',
             s.default_seek_point_spacing),
            ('Default Sleep Period (seconds)', s.default_sleep_period)
        )

        return StatusTable(self.name, rows)
    

    def _get_recording_dir_status_tables(self):

        
        def get_recording_dir_status_table(s):

            name = f'{self.name} - Directory "{s.dir_path}"'

            rows = (
                ('Directory Path', s.dir_path),
                ('Search Recursively', s.search_recursively),
                ('Seek Point Spacing (seconds)', s.seek_point_spacing),
                ('Sleep Period (seconds)', s.sleep_period)
            )

            return StatusTable(name, rows)

        return [
            get_recording_dir_status_table(s)
            for s in self.settings.recording_dirs]
        
        
class _ConvertThread(Thread):


    def __init__(self, settings):
        super().__init__()
        self._settings = settings
        self._glob_pattern = _create_glob_pattern(settings)
        self._stop_event = threading.Event()


    def run(self):

        while not self._stop_event.is_set():

            # Get paths of all WAVE files in recording directory.
            dir_path = self._settings.dir_path
            _logger.info(
                f'Checking directory "{dir_path}" for WAVE files to convert '
                f'to FLAC...')
            input_file_paths = sorted(dir_path.glob(self._glob_pattern))

            # Convert files.
            for file_path in input_file_paths:

                self._convert_file(file_path)

                # Check for stop event after each file.
                if self._stop_event.is_set():
                    return
                
            self._stop_event.wait(self._settings.sleep_period)


    def _convert_file(self, input_file_path):

        """
        Convert the specified WAVE file to a FLAC file and then delete the
        WAVE file.
        """

        # Get output file paths.
        in_progress_file_path = input_file_path.with_suffix(
            _IN_PROGRESS_FILE_NAME_EXTENSION)
        output_file_path = input_file_path.with_suffix(
            _FLAC_FILE_NAME_EXTENSION)

        # Get `flac` command to run.
        seek_point_spacing = f'{self._settings.seek_point_spacing}s'
        command = [
            'flac',
            '-f',  # force output file overwrite
            '-S', seek_point_spacing,
            '-o', str(in_progress_file_path),
            str(input_file_path)]

        # print(
        #     f'Converting WAVE file "{input_file_path}" to FLAC file '
        #     f'"{output_file_path}" with command {command}...')
        
        _logger.info(
            f'Converting WAVE file "{input_file_path}" to FLAC file '
            f'"{output_file_path}" with command {command}...')

        # Run command.
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except Exception as e:
            _logger.warning(
                f'Attempt to run command {command} to convert WAVE file '
                f'to FLAC file raised exception. Error message was: {e}')
            return

        # Check command result.
        if result.returncode != 0:
            _logger.warning(
                f'Command {command} to convert WAVE file to FLAC file '
                f'failed with exit code {result.returncode}. Standard '
                f'error was: {result.stderr.strip()}')
            return
        
        # Rename output file to remove ".in_progress" suffix.
        try:
            in_progress_file_path.rename(output_file_path)
        except Exception as e:
            _logger.warning(
                f'Attempt to rename file "{in_progress_file_path}" to '
                f'"{output_file_path}" raised an exception. '
                f'Error message was: {e}')
            return

        # Delete input file.
        try:
            input_file_path.unlink()
        except Exception as e:
            _logger.warning(
                f'Attempt to delete file "{input_file_path}" raised an '
                f'exception. Error message was: {e}')


def _get_absolute_path(path):
    if path.is_absolute():
        return path
    else:
        return Path.cwd() / path


def _create_glob_pattern(settings):
    pattern = '*.wav'
    if settings.search_recursively:
        pattern = f'**/{pattern}'
    return pattern
