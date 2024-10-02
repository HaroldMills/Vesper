from logging.handlers import QueueHandler
from pathlib import Path
import logging
import multiprocessing as mp
import time

from botocore.client import Config
import boto3

from vesper.recorder.settings import Settings
from vesper.recorder.sidecar import Sidecar
from vesper.util.bunch import Bunch
import vesper.recorder.error_utils as error_utils


# Get `multiprocessing` context object that uses the *spawn* start method.
# We use this context object to create processes and queues consistently
# on all platforms.
_context = mp.get_context('spawn')
Process = _context.Process
Event = _context.Event


_LOGGING_LEVEL = logging.INFO
_DEFAULT_SLEEP_PERIOD = 10                  # seconds
_DEFAULT_FILE_NAME_PATTERN = '*'
_DEFAULT_SEARCH_RECURSIVELY = False
_DEFAULT_BOTO_READ_TIMEOUT = 300            # seconds
_DEFAULT_DELETE_UPLOADED_FILES = True
_DEFAULT_UPLOADED_FILE_DIR_PATH = None


# Example sidecar settings:
#
#     sleep_period: 2
#     default_aws_profile_name: harold-harold
#     default_s3_bucket_name: vesper-test
#     default_s3_object_key_prefix: recordings
#     boto_read_timeout: 300
#     upload_dirs:
#         - dir_path: 'Recordings - S3'
#             file_name_pattern: '*.wav'
#             search_recursively: false
#             aws_profile_name: harold-harold
#             s3_bucket_name: vesper-test
#             s3_object_key_prefix: recordings
#             delete_uploaded_files: false
#             uploaded_file_dir_path: 'Recordings - S3/Uploaded'


class S3FileUploaderSidecar(Sidecar):


    type_name = 'S3 File Uploader'


    @staticmethod
    def parse_settings(settings):

        sleep_period = float(settings.get(
            'sleep_period', _DEFAULT_SLEEP_PERIOD))
        
        default_aws_profile_name = settings.get('default_aws_profile_name')

        default_s3_bucket_name = settings.get('default_s3_bucket_name')

        default_s3_object_key_prefix = settings.get(
            'default_s3_object_key_prefix')
        
        boto_read_timeout = float(settings.get(
            'boto_read_timeout', _DEFAULT_BOTO_READ_TIMEOUT))
        
        def parse_upload_dir_settings(mapping):

            s = Settings(mapping)

            dir_path = Path(s.get_required('dir_path', 'S3 upload directory'))

            file_name_pattern = s.get(
                'file_name_pattern', _DEFAULT_FILE_NAME_PATTERN)
            
            search_recursively = s.get(
                'search_recursively', _DEFAULT_SEARCH_RECURSIVELY)
            
            aws_profile_name = s.get(
                'aws_profile_name', default_aws_profile_name)
            
            if aws_profile_name is None:
                handle_missing_setting(dir_path, 'aws_profile_name')
            
            s3_bucket_name = s.get(
                's3_bucket_name', default_s3_bucket_name)
            
            if s3_bucket_name is None:
                handle_missing_setting(dir_path, 's3_bucket_name')

            s3_object_key_prefix = s.get(
                's3_object_key_prefix', default_s3_object_key_prefix)

            delete_uploaded_files = s.get(
                'delete_uploaded_files', _DEFAULT_DELETE_UPLOADED_FILES)
            
            uploaded_file_dir_path = s.get(
                'uploaded_file_dir_path', _DEFAULT_UPLOADED_FILE_DIR_PATH)
            if uploaded_file_dir_path is not None:
                uploaded_file_dir_path = Path(uploaded_file_dir_path)
            
            return Bunch(
                dir_path=dir_path,
                file_name_pattern=file_name_pattern,
                search_recursively=search_recursively,
                aws_profile_name=aws_profile_name,
                s3_bucket_name=s3_bucket_name,
                s3_object_key_prefix=s3_object_key_prefix,
                delete_uploaded_files=delete_uploaded_files,
                uploaded_file_dir_path=uploaded_file_dir_path)

        upload_dirs = [
            parse_upload_dir_settings(s)
            for s in settings.get_required('upload_dirs')]

        return Bunch(
            sleep_period=sleep_period,
            default_aws_profile_name=default_aws_profile_name,
            default_s3_bucket_name=default_s3_bucket_name,
            default_s3_object_key_prefix=default_s3_object_key_prefix,
            boto_read_timeout=boto_read_timeout,
            upload_dirs=upload_dirs)
            

    def __init__(self, name, settings, context):
        super().__init__(name, settings, context)
        self._process = _S3FileUploaderProcess(name, settings, context)


    def start(self):
        self._process.start()


    def stop(self):
        self._process.stop()


def handle_missing_setting(dir_path, name):
    raise ValueError(
        f'For S3 file upload directory "{dir_path}", setting "{name}" '
        f'and parent sidecar setting "default_{name}" are both absent. '
        f'At least one of them must be specified.')


class _S3FileUploaderProcess(Process):


    def __init__(self, name, settings, context):

        super().__init__()

        self._name = name
        self._settings = settings
        self._context = context

        self._logging_queue = self._context.multiprocess_logging_queue
        self._boto_config = _create_boto_config(self._settings)
        self._stop_event = Event()


    @property
    def name(self):
        return self._name
    

    def run(self):

        try:

            self._configure_logging()

            while not self._stop_event.is_set():

                for dir_settings in self._settings.upload_dirs:
                    self._upload_files(dir_settings)

                time.sleep(self._settings.sleep_period)

        except KeyboardInterrupt:
            pass

        except Exception:
            error_utils.handle_top_level_exception(
                'S3 file uploader process')


    def _configure_logging(self):
        
        # Get the root logger for this process.
        logger = logging.getLogger()

        # Add handler to root logger that forwards all log messages to
        # the logging process.
        handler = QueueHandler(self._logging_queue)
        logger.addHandler(handler)

        # Set logging level for this process.
        logger.setLevel(_LOGGING_LEVEL)

        # Get the logger for this module.
        self._logger = logging.getLogger(__name__)


    def _upload_files(self, dir_settings):

        s = dir_settings

        dir_path = _get_absolute_path(s.dir_path)

        self._logger.info(
            f'Checking directory "{dir_path}" for files to upload...')

        pattern = _get_glob_pattern(
            s.file_name_pattern, s.search_recursively)

        file_paths = dir_path.glob(pattern)

        for file_path in file_paths:
            rel_file_path = file_path.relative_to(dir_path)
            self._upload_file(dir_path, rel_file_path, dir_settings)


    def _upload_file(self, dir_path, rel_file_path, dir_settings):

        s = dir_settings

        # Get S3 object key for file.
        object_key = '/'.join(rel_file_path.parts)
        if s.s3_object_key_prefix is not None:
            object_key = f'{s.s3_object_key_prefix}/{object_key}'
  
        # Get absolute file path.
        abs_file_path = dir_path / rel_file_path

        self._logger.info(
            f'Uploading file "{abs_file_path}" to S3 bucket '
            f'"{s.s3_bucket_name}", object key "{object_key}"...')
        
        try:

            # Create new session for each upload to help ensure that
            # session timeouts will not be an issue.
            session = boto3.Session(profile_name=s.aws_profile_name)

            s3 = session.client('s3', config=self._boto_config)

            s3.upload_file(abs_file_path, s.s3_bucket_name, object_key)

        except Exception as e:
            # upload failed

            self._logger.warning(
                f'Failed to upload file "{abs_file_path}" to S3 bucket '
                f'"{s.s3_bucket_name}", object key "{object_key}". '
                f'Exception message was: {e}')

        else:
            # upload succeeded

            if s.uploaded_file_dir_path is not None:
                self._move_uploaded_file(
                    abs_file_path, s.uploaded_file_dir_path, rel_file_path)
                
            elif s.delete_uploaded_files:
                self._delete_file(abs_file_path)
                self._delete_empty_ancestor_dirs(dir_path, rel_file_path)


    def _move_uploaded_file(
            self, abs_from_file_path, to_dir_path, rel_to_file_path):

        to_dir_path = _get_absolute_path(to_dir_path)
        abs_to_file_path = to_dir_path / rel_to_file_path
        to_parent_dir_path = abs_to_file_path.parent

        self._logger.info(
            f'Moving uploaded file "{abs_from_file_path}" to '
            f'"{abs_to_file_path}"...')

        # Create new parent directory for uploaded file if needed.
        try:
            to_parent_dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._logger.warning(
                f'Could not create new parent directory '
                f'"{to_parent_dir_path}" for uploaded file '
                f'"{abs_to_file_path}". Exception message was: {e}')
            return

        # Move uploaded file.
        try:
            abs_from_file_path.rename(abs_to_file_path)
        except Exception as e:
            self._logger.warning(
                f'Could not move uploaded file "{abs_from_file_path}" '
                f'to directory "{to_parent_dir_path}". Exception message '
                f'was: {e}')
        

    def _delete_file(self, file_path):

        self._logger.info(f'Deleting file "{file_path}" uploaded to S3...')
        
        try:
            file_path.unlink()

        except Exception as e:
            self._logger.warning(
                f'Could not delete file "{file_path}" uploaded to S3. '
                f'Exception message was: {e}')
            

    def _delete_empty_ancestor_dirs(self, upload_dir_path, rel_file_path):

        """
        Deletes the directories of `file_path.parents[:-1] up until
        the first non-empty directory. Does not consider
        `file_path.parents[-1]` since it is always '.', which we
        never want to delete.
        """


        # Iterate over parent directories of `file_path` in reverse
        # order, up to upload directory. The parent directories are
        # all upload directory subdirectories.
        for rel_subdir_path in rel_file_path.parents[:-1]:

            # We could just invoke `dir_path.rmdir` instead of checking
            # if the directory is empty first, and ignore any exception
            # that it raises. That should work, deleting an empty
            # directory and doing nothing for a non-empty one. However,
            # I don't like the idea of invoking `rmdir` on directories
            # that I know I don't want to delete, counting on that
            # method to protect me from disaster! It also wouldn't
            # allow us to detect failed attempts to delete empty
            # directories.

            abs_subdir_path = upload_dir_path / rel_subdir_path

            if _is_dir_empty(abs_subdir_path):
                # upload subdirectory empty

                self._logger.info(
                    f'Deleting empty upload subdirectory '
                    f'"{abs_subdir_path}"...')
                    
                try:
                    abs_subdir_path.rmdir()

                except Exception as e:
                    self._logger.warning(
                        f'Could not delete empty upload subdirectory '
                        f'"{abs_subdir_path}". Error message was: {e}')
                    
            else:
                # upload subdirectory not empty

                # We can stop here, since any further parent directories
                # will be ancestors of this one and hence not empty either.
                break
            
            
    def stop(self):
        self._stop_event.set()
        self.join()


def _create_boto_config(settings):
    return Config(
        retries={
            'mode': 'standard',
            'max_attempts': 5
        },
        read_timeout=settings.boto_read_timeout)


def _get_absolute_path(path):
    if path.is_absolute():
        return path
    else:
        return Path.cwd() / path


def _get_glob_pattern(file_name_pattern, search_recursively):
    if search_recursively:
        return f'**/{file_name_pattern}'
    else:
        return file_name_pattern
    

def _is_dir_empty(dir_path):
    child_paths = tuple(dir_path.iterdir())
    return len(child_paths) == 0
