"""Module containing class `RefreshRecordingAudioFilePathsCommand`."""


from pathlib import Path, PureWindowsPath
import logging
import time


from vesper.command.command import Command
from vesper.django.app.models import RecordingFile
from vesper.singleton.recording_manager import recording_manager
import vesper.command.command_utils as command_utils
import vesper.util.text_utils as text_utils


_LOGGING_PERIOD = 1000


class RefreshRecordingAudioFilePathsCommand(Command):
    
    
    extension_name = 'refresh_recording_audio_file_paths'
    
    
    def execute(self, job_info):
        
        self._job_info = job_info
        self._logger = logging.getLogger()

        recording_file_paths = self._get_recording_file_paths()
        
        self._refresh_recording_file_paths(recording_file_paths)
        
        return True
    
    
    def _get_recording_file_paths(self):
        
        recording_dir_paths = recording_manager.recording_dir_paths
        
        self._logger.info('Recording directories are:')
        for path in recording_dir_paths:
            self._logger.info('    {}'.format(path))
        
        self._logger.info(
            'Building mapping from recording directory file names to '
            'relative file paths...')
        
        # Reverse directory paths so that if a file name occurs in multiple
        # directories we will wind up mapping the file name to the path of
        # the first recording directory in which it occurs.
        recording_dir_paths = reversed(recording_dir_paths)
        
        recording_file_paths = {}
        
        for dir_path in recording_dir_paths:
            dir_path = Path(dir_path)
            if dir_path.exists():
                self._get_recording_file_paths_aux(
                    dir_path, dir_path, recording_file_paths)
                
        return recording_file_paths
            
            
    def _get_recording_file_paths_aux(
            self, dir_path, recording_dir_path, recording_file_paths):
        
        # Visit directories before files, depth-first. This gives
        # shallower files precedence over deeper, identically-named
        # files, in the sense that their paths will wind up in the
        # `recording_file_paths` mapping.
        
        children = list(dir_path.iterdir())
        
        for child in children:
            if child.is_dir():
                self._get_recording_file_paths_aux(
                    child, recording_dir_path, recording_file_paths)
                
                
        # Visit files.
        
        for child in children:
            
            if not child.is_dir():
                
                try:
                    rel_path = child.relative_to(recording_dir_path)
                except ValueError:
                    self._logger.error(
                        ('    Could not get path "{}" relative to directory '
                         '"{}".').format(child, recording_dir_path))
                    
                # We store all paths in the archive database as POSIX
                # paths, even on Windows, for portability, since Python's
                # `pathlib` module recognizes the slash as a path separator
                # on all platforms, but not the backslash.
                recording_file_paths[child.name] = rel_path.as_posix()
                
    
    
    def _refresh_recording_file_paths(self, recording_file_paths):
        
        start_time = time.time()
        
        file_count = RecordingFile.objects.count()
        count_text = text_utils.create_count_text(file_count, 'recording file')
         
        self._logger.info('Command will visit {}.'.format(count_text))
        
        updated_count = 0
        
        for i, file_ in enumerate(RecordingFile.objects.all()):
            
            visited_count = i + 1
            
            if visited_count % _LOGGING_PERIOD == 0:
                self._logger.info(
                    '    Visited {} files...'.format(visited_count))
                
            old_path = file_.path
            file_name = _get_file_name(old_path)
            
            new_path = recording_file_paths.get(file_name)
            
            if new_path is None:
                self._logger.warning(
                    ('    Could not find recording file "{}" in recording '
                     'directories.').format(file_name))
                
            elif new_path != old_path:
                # self._logger.info(
                #     '        Update "{}" to "{}"...'.format(
                #         old_path, new_path))
                file_.path = new_path
                file_.save()
                updated_count += 1
                
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, visited_count, 'files')
                
        self._logger.info((
            'Updated paths for {} of {} visited recording files{}.').format(
                updated_count, visited_count, timing_text))
        


def _get_file_name(path):
    
    # Note that we always construct a `PureWindowsPath` here, even on Unix.
    # Then `p.name` gives us what we want regardless of platform. If we
    # construct a `Path` instead, then for a Windows path stored in the
    # database, `p.name` gives us the entire Windows path on macOS and
    # Linux rather than just the file name.
    
    p = PureWindowsPath(path)
    return p.name
