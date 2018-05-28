"""Module containing class `Recording Manager`."""


from pathlib import Path
import logging


class RecordingManager:


    """
    Manages the recordings of a Vesper archive.
    
    The main responsibility of a recording manager is to convert
    recording file paths between relative and absolute forms. The
    relative form of a recording file path, stored in the archive
    database, is converted to its absolute form by appending it
    to the absolute path of one of the archive's *recording
    directories*. The absolute form is converted to the relative
    form by removing the initial recording directory path.
    
    It is common for there to be only one recording directory for
    an archive, but in some cases (for example, if the recordings
    of a large archive are located on more than one disk) an
    archive may have more than one recording directory. When there
    is more than one recording directory, care must be taken to
    ensure that any relative recording file path exists in only one
    recording directory. This can be accomplished by making
    recording file names unique within an archive, a common
    practice.
    
    Parameters
    ----------
    archive_dir_path: str or pathlib.Path object
        The absolute path of the archive of this manager.
        
    recording_dir_paths: sequence of str or pathlib.Path objects
        Each of the specified paths must be the path of a recording
        directory. Each path may be either absolute or relative:
        if a path is relative, it is relative to the archive
        directory. A specified recording directory does not have to
        exist, though of course if it does not any recordings that
        are supposed to be in it cannot be accessed. In order to
        ensure proper operation for case-insensitive file systems,
        no pair of recording directory paths can differ only by
        alphabetic case, even for a case-sensitive file system.
        
    Attributes
    ----------
    archive_dir_path: pathlib.Path object
        The absolute path of the archive of this manager.
        
    recording_dir_paths: tuple of pathlib.Path objects
        The recording directory paths of this manager.
        
    Raises
    ------
    ValueError:
        if the specified archive directory path is not absolute.
    """
    
    
    def __init__(self, archive_dir_path, recording_dir_paths):
        
        self._archive_dir_path = _get_path_object(archive_dir_path)
        
        self._check_archive_dir_path()
        
        self._recording_dir_paths = \
            self._get_recording_dir_paths(recording_dir_paths)
            
        self._lowered_recording_dir_paths = \
            tuple(Path(str(p).lower()) for p in self._recording_dir_paths)
        
        self._absolute_file_path_cache = {}

        
    def _check_archive_dir_path(self):
        if not self.archive_dir_path.is_absolute():
            raise ValueError(
                ('Archive directory path "{}" specified to recording '
                 'manager is not absolute.').format(self.archive_dir_path))
            
            
    def _get_recording_dir_paths(self, paths):
        
        # Get all recording dir paths as `Path` objects.
        paths = [_get_path_object(p) for p in paths]
        
        vetted_paths = []
        lowered_to_original = {}
        logger = logging.getLogger()
        
        for path in paths:
            
            if not path.is_absolute():
                path = self.archive_dir_path / path
                
            lowered_path = str(path).lower()
            
            original = lowered_to_original.get(lowered_path)
            
            if original is not None:
                # have already seen this path or one that is identical to
                # it except for alphabetic case
                
                if original == path:
                    s = 'a duplicate'
                else:
                    s = 'considered a duplicate of "{}"'.format(original)
                    
                logger.warning((
                    'Recording directory path "{}" specified to recording '
                    'manager is {} and will be ignored.').format(path, s))
            
            else:
                # have not already seen this path
                
                vetted_paths.append(path)
                lowered_to_original[lowered_path] = path
                
        return tuple(vetted_paths)
        

    @property
    def archive_dir_path(self):
        return self._archive_dir_path
    
    
    @property
    def recording_dir_paths(self):
        return self._recording_dir_paths
    
    
    def get_absolute_recording_file_path(self, relative_path):
        
        """
        Gets the absolute version of a relative recording file path.
        
        This method looks for the specified relative path within the
        recording directories, and returns the absolute version of the
        path if found. The recording directories are searched in order.
        
        Parameters
        ----------
        relative_path: str or pathlib.Path
            The relative path for which to find the absolute path.
            
        Returns
        -------
        pathlib.Path
            The absolute version of the specified relative path.
            
        Raises
        ------
        ValueError:
            if the specified path is absolute or does not exist in any
            recording directory.
        """
        
        # Ensure that path is a `Path` object.
        path = _get_path_object(relative_path)
        
        if path.is_absolute():
            raise ValueError(
                'Recording file path "{}" is already absolute.'.format(path))
        
        else:
            # `path` is relative
            
            try:
                return self._absolute_file_path_cache[path]
            
            except KeyError:
                
                for dir_path in self.recording_dir_paths:
                
                    abs_path = dir_path / path
                    
                    if abs_path.exists():
                        self._absolute_file_path_cache[path] = abs_path
                        return abs_path
                
                # If we get here, the specified path does not exist in
                # any recording directory.
                    
                start = (
                    'Recording file path "{}" could not be made '
                    'absolute since ').format(path)
                     
                num_recording_dirs = len(self.recording_dir_paths)
                 
                if num_recording_dirs == 0:
                    end = 'there are no recording directories.'
                     
                elif num_recording_dirs == 1:
                    
                    if not dir_path.exists():
                        end = (
                            'the recording directory "{}" could not be '
                            'found.').format(self.recording_dir_paths[0])
                    else:
                        end = (
                            'it is not in the recording directory '
                            '"{}".').format(self.recording_dir_paths[0])
                         
                else:
                    end = (
                        'it is not in any of the recording directories '
                        '{}.').format(self._create_recording_dirs_list())
                         
                raise ValueError(start + end)
        
    
    def _create_recording_dirs_list(self):
        return str([str(p) for p in self.recording_dir_paths])


    def get_relative_recording_file_path(self, absolute_path):
        
        """
        Gets the relative version of an absolute recording file path.
        
        The path is made relative with respect to the first recording
        directory whose path starts it, disregarding alphabetic case.
        Note that the specified path does not have to exist: it only
        has to start with a recording directory path.
        
        Parameters
        ----------
        absolute_path: str or pathlib.Path
            The absolute path for which to find the relative path.
        
        Returns
        -------
        recording_dir_path: pathlib.Path
            The path of the first recording directory whose path starts
            `absolute_path`.
        rel_path: pathlib.Path
            The path relative to `recording_dir_path` of `absolute_path`.
            
        Raises
        ------
        ValueError
            If the specified path is relative, or does not start with
            a recording directory path.
        """
        
        # Ensure that path is a `Path` object.
        path = _get_path_object(absolute_path)
        
        if not path.is_absolute():
            raise ValueError(
                'Recording file path "{}" is already relative.'.format(path))
            
        else:
            # `path` is absolute
            
            # Get lower-case version of path for comparison to
            # lower-case versions of recording directory paths.
            lowered_path = Path(str(path).lower())
            
            for dir_path, lowered_dir_path in \
                    zip(self.recording_dir_paths,
                        self._lowered_recording_dir_paths):
                
                try:
                    lowered_rel_path = \
                        lowered_path.relative_to(lowered_dir_path)
                    
                except ValueError:
                    continue
                
                else:
                    num_parts = len(lowered_rel_path.parts)
                    parts = path.parts[-num_parts:]
                    rel_path = Path(*parts)
                    return dir_path, rel_path
            
            # If we get here, the specified path is not inside any of the
            # recording directories.
            
            start = (
                'Recording file path "{}" could not be made relative '
                'since ').format(path)
                 
            num_recording_dirs = len(self.recording_dir_paths)
             
            if num_recording_dirs == 0:
                end = 'there are no recording directories.'
                 
            elif num_recording_dirs == 1:
                end = 'it is not in the recording directory "{}".'.format(
                    self.recording_dir_paths[0])
                     
            else:
                end = \
                    'it is not in any of the recording directories {}.'.format(
                        self._create_recording_dirs_list())
                     
            raise ValueError(start + end)


def _get_path_object(p):
    return p if isinstance(p, Path) else Path(p)
