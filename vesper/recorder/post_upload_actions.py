"""
Module containing post-upload action classes for uploaded files.

After the Vesper Recorder uploads a file to a cloud storage service
it can perform an action on the file, such as deleting or moving it.
The classes of this module implement such actions.
"""


import logging
import platform

from vesper.recorder.settings import Settings
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


class _PostUploadActionError(Exception):
    pass


class _PostUploadAction:


    type_name = None


    @staticmethod
    def parse_settings(mapping):
        return Bunch()
    

    @staticmethod
    def get_status_table_rows(settings):
        return ()
    

    def __init__(self, upload_dir_path, settings):
        self._upload_dir_path = upload_dir_path
        self._settings = settings


    def execute(self, rel_file_path):
        raise NotImplementedError()
    

    def _delete_empty_ancestor_dirs(self, rel_file_path):

        """
        Deletes the directories of `rel_file_path.parents[:-1] up until
        the first non-empty directory. Does not consider
        `rel_file_path.parents[-1]` since it is always '.', or the upload
        directory, which we never want to delete.
        """


        # Iterate over parent directories of `rel_file_path` in reverse
        # order, up to upload directory. The parent directories are
        # all upload directory subdirectories.
        for rel_subdir_path in rel_file_path.parents[:-1]:

            # We could just invoke `abs_subdir_path.rmdir` instead of checking
            # if the directory is empty first, and ignore any exception that it
            # raises. That should work, deleting an empty directory and doing
            # nothing for a non-empty one. However, I don't like the idea of
            # invoking `rmdir` on directories that I know I don't want to delete,
            # counting on that method to protect me from disaster! It also
            # wouldn't allow us to detect failed attempts to delete empty
            # directories.

            abs_subdir_path = self._upload_dir_path / rel_subdir_path

            if _is_dir_empty(abs_subdir_path):
                # upload subdirectory empty

                _logger.info(
                    f'Deleting empty upload subdirectory '
                    f'"{abs_subdir_path}"...')
                    
                try:
                    abs_subdir_path.rmdir()

                except Exception as e:
                    raise _PostUploadActionError(
                        f'Could not delete empty upload subdirectory '
                        f'"{abs_subdir_path}": {e}')
                    
            else:
                # upload subdirectory not empty

                # We can stop here, since any further parent directories
                # will be ancestors of this one and hence not empty either.
                break
        
        
def _is_dir_empty(dir_path):

    child_paths = tuple(dir_path.iterdir())

    if len(child_paths) == 0:
        return True
    
    if platform.system() == 'Darwin' and len(child_paths) == 1 and \
            child_paths[0].name == '.DS_Store':
        # on macOS and directory contains only a `.DS_Store` file
        
        # Delete `.DS_Store` file.
        file_path = dir_path / '.DS_Store'
        try:
            file_path.unlink()
        except Exception as e:
            _logger.warning(
                f'Could not delete lone ".DS_Store" file from directory '
                f'"{dir_path}", so directory will not be deleted. '
                f'Error message was: {e}')
            return False
        
        return True
    
    return False


class _DeleteFileAction(_PostUploadAction):


    type_name = 'Delete File'


    def execute(self, rel_file_path):
    
        abs_file_path = self._upload_dir_path / rel_file_path

        _logger.info(f'Deleting file "{abs_file_path}" uploaded to S3...')

        # Delete file.
        try:
            abs_file_path.unlink()
        except Exception as e:
            raise _PostUploadActionError(f'Could not delete file: {e}')

        # If we make it here, the file was successfully deleted.
        self._delete_empty_ancestor_dirs(rel_file_path)


class _MoveFileAction(_PostUploadAction):


    type_name = 'Move File'


    @staticmethod
    def parse_settings(mapping):
        s = Settings(mapping)
        dest_dir_path = s.get_required('dest_dir_path', 'post-upload action')
        return Bunch(dest_dir_path=dest_dir_path)
   

    @staticmethod
    def get_status_table_rows(settings):
        return (
            ('Post-upload Action Destination Directory',
             settings.dest_dir_path),)
    

    def __init__(self, upload_dir_path, settings):
        super().__init__(upload_dir_path, settings)
        self._dest_dir_path = settings.dest_dir_path


    def execute(self, rel_file_path):
    
        abs_file_path = self._upload_dir_path / rel_file_path
        abs_dest_file_path = self._dest_dir_path / rel_file_path
        dest_parent_dir_path = abs_dest_file_path.parent

        _logger.info(
            f'Moving uploaded file "{abs_file_path}" to '
            f'"{abs_dest_file_path}"...')

        # Create new parent directory for file to be moved if needed.
        try:
            dest_parent_dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise _PostUploadActionError(
                f'Could not create new parent directory '
                f'"{dest_parent_dir_path}" for uploaded file '
                f'"{abs_dest_file_path}": {e}')
 
        # Move file.
        try:
            abs_file_path.rename(abs_dest_file_path)
        except Exception as e:
            raise _PostUploadActionError(
                f'Could not move uploaded file "{abs_file_path}" '
                f'to directory "{dest_parent_dir_path}": {e}')

        # If we make it here, the file was successfully moved.
        self._delete_empty_ancestor_dirs(rel_file_path)


_action_classes = {
    c.type_name: c
    for c in (_DeleteFileAction, _MoveFileAction)
}


def parse_action_settings(mapping):

    if mapping is None:
        return None
    
    else:

        # Get action type from settings.
        settings = Settings(mapping)
        type = settings.get_required('type', 'post-upload action')

        # Get action class for action type.
        try:
            cls = _action_classes[type]
        except KeyError:
            raise ValueError(f'Unrecognized post-upload action type "{type}".')
        
        # Get settings specific to action type.
        mapping = settings.get('settings', {})
        settings = cls.parse_settings(mapping)
        
        return Bunch(type=type, settings=settings)
                

def create_action(settings, upload_dir_path):
    cls = _action_classes[settings.type]
    return cls(upload_dir_path, settings.settings)


def get_action_status_table_rows(settings):

    if settings is None:
        return (('Post-upload Action', 'None'),)
    
    else:
        cls = _action_classes[settings.type]
        return (
            ('Post-upload Action', settings.type),
            *cls.get_status_table_rows(settings.settings))
