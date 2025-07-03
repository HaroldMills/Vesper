from collections import deque
from pathlib import Path
from threading import Thread
import logging
import multiprocessing as mp
import threading

from botocore.client import Config
import boto3

from vesper.recorder.settings import Settings
from vesper.recorder.sidecar import Sidecar
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch
import vesper.recorder.post_upload_actions as post_upload_actions
import vesper.util.yaml_utils as yaml_utils


_logger = logging.getLogger(__name__)


_DEFAULT_FILE_NAME_PATTERN = '*'
_DEFAULT_SEARCH_RECURSIVELY = True
_DEFAULT_BOTO_READ_TIMEOUT = 300            # seconds
_DEFAULT_POST_UPLOAD_ACTION = None
_DEFAULT_SLEEP_PERIOD = 60                  # seconds
_STATE_FILE_NAME = '.S3 File Uploader State.yaml'


# Example sidecar settings:
#
#     default_aws_profile_name: harold-harold
#     default_s3_bucket_name: vesper-test
#     default_s3_object_key_prefix: recordings
#     boto_read_timeout: 300
#     default_sleep_period: 60
#     upload_dirs:
#         - dir_path: 'Recordings - S3'
#           file_name_pattern: '*.wav'
#           search_recursively: false
#           aws_profile_name: harold-harold
#           s3_bucket_name: vesper-test
#           s3_object_key_prefix: recordings
#           post_upload_action:
#               name: Move File
#               dir_path: 'Recordings - S3/Uploaded'
#           sleep_period: 30


# Example "S3 File Uploader State.yaml" file:
#
#     uploaded_file_paths:
#         - 2020-01-01_01-01-01.wav
#
#     failed_uploads:
#         - file_path: 2020-01-01_01-01-02.wav
#           failure_count: 1


class S3FileUploaderSidecar(Sidecar):


    type_name = 'S3 File Uploader'


    @staticmethod
    def parse_settings(settings):

        default_aws_profile_name = settings.get('default_aws_profile_name')

        default_s3_bucket_name = settings.get('default_s3_bucket_name')

        default_s3_object_key_prefix = settings.get(
            'default_s3_object_key_prefix')
        
        default_boto_read_timeout = float(settings.get(
            'default_boto_read_timeout', _DEFAULT_BOTO_READ_TIMEOUT))
        
        default_post_upload_action = settings.get(
            'default_post_upload_action', _DEFAULT_POST_UPLOAD_ACTION)
        
        default_sleep_period = float(settings.get(
            'default_sleep_period', _DEFAULT_SLEEP_PERIOD))
        

        def parse_upload_dir_settings(mapping):

            s = Settings(mapping)

            dir_path = _get_absolute_path(
                Path(s.get_required('dir_path', 'S3 upload directory')))

            file_name_pattern = s.get(
                'file_name_pattern', _DEFAULT_FILE_NAME_PATTERN)
            
            search_recursively = s.get(
                'search_recursively', _DEFAULT_SEARCH_RECURSIVELY)
            
            aws_profile_name = s.get(
                'aws_profile_name', default_aws_profile_name)
            
            if aws_profile_name is None:
                _handle_missing_setting(dir_path, 'aws_profile_name')
            
            s3_bucket_name = s.get(
                's3_bucket_name', default_s3_bucket_name)
            
            if s3_bucket_name is None:
                _handle_missing_setting(dir_path, 's3_bucket_name')

            s3_object_key_prefix = s.get(
                's3_object_key_prefix', default_s3_object_key_prefix)
            
            boto_read_timeout = s.get(
                'boto_read_timeout', default_boto_read_timeout)
            
            post_upload_action = post_upload_actions.parse_action_settings(
                s.get('post_upload_action', default_post_upload_action))
            
            sleep_period = s.get('sleep_period', default_sleep_period)

            return Bunch(
                dir_path=dir_path,
                file_name_pattern=file_name_pattern,
                search_recursively=search_recursively,
                aws_profile_name=aws_profile_name,
                s3_bucket_name=s3_bucket_name,
                s3_object_key_prefix=s3_object_key_prefix,
                boto_read_timeout=boto_read_timeout,
                post_upload_action=post_upload_action,
                sleep_period=sleep_period)
        
 
        upload_dirs = [
            parse_upload_dir_settings(s)
            for s in settings.get_required('upload_dirs')]

        return Bunch(
            default_aws_profile_name=default_aws_profile_name,
            default_s3_bucket_name=default_s3_bucket_name,
            default_s3_object_key_prefix=default_s3_object_key_prefix,
            default_boto_read_timeout=default_boto_read_timeout,
            default_sleep_period=default_sleep_period,
            upload_dirs=upload_dirs)
            

    def __init__(self, name, settings, context):
        super().__init__(name, settings, context)
        self._stop_event = mp.Event()


    def _run(self):
            
        # Create threads.
        threads = [_UploadThread(s) for s in self._settings.upload_dirs]

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
        dir_tables = self._get_upload_dir_status_tables()
        return [main_table] + dir_tables
    

    def _get_main_status_table(self):

        s = self.settings

        rows = (
            ('Default AWS Profile Name', s.default_aws_profile_name),
            ('Default S3 Bucket Name', s.default_s3_bucket_name),
            ('Default S3 Object Key Prefix', s.default_s3_object_key_prefix),
            ('Default Boto Read Timeout (seconds)',
             s.default_boto_read_timeout),
            ('Default Sleep Period (seconds)', s.default_sleep_period),
        )

        return StatusTable(self.name, rows)
    

    def _get_upload_dir_status_tables(self):

        
        def get_upload_dir_status_table(s):

            name = f'{self.name} - Directory "{s.dir_path}"'

            rows = (

                ('Directory Path', s.dir_path),
                ('File Name Pattern', s.file_name_pattern),
                ('Search Recursively', s.search_recursively),
                ('AWS Profile Name', s.aws_profile_name),
                ('S3 Bucket Name', s.s3_bucket_name),
                ('S3 Object Key Prefix', s.s3_object_key_prefix),
                ('Boto Read Timeout (seconds)', s.boto_read_timeout)) + \
                post_upload_actions.get_action_status_table_rows(
                    s.post_upload_action) + \
                (('Sleep Period (seconds)', s.sleep_period),)

            return StatusTable(name, rows)

        return [
            get_upload_dir_status_table(s)
            for s in self.settings.upload_dirs]


def _handle_missing_setting(dir_path, name):
    raise KeyError(
        f'For S3 file upload directory "{dir_path}", setting "{name}" '
        f'and parent sidecar setting "default_{name}" are both absent. '
        f'At least one of them must be specified.')


class _UploadThread(Thread):


    def __init__(self, settings):
        super().__init__()
        self._settings = settings
        self._glob_pattern = _create_glob_pattern(settings)
        self._boto_config = _create_boto_config(settings)
        self._post_upload_action = _create_post_upload_action(settings)
        self._stop_event = threading.Event()


    def run(self):
        while not self._stop_event.is_set():
            self._upload_files()
            self._stop_event.wait(self._settings.sleep_period)


    def _upload_files(self):

        dir_path = self._settings.dir_path

        _logger.info(f'Checking directory "{dir_path}" for files to upload...')

        with _UploaderState(dir_path) as state:

            # Note that we are careful in this `with` statement body that
            # our modifications to the lists of uploaded file paths and
            # failed uploads are reflected in the `state` object. This
            # ensures that the context manager will write the changes to
            # the state file when it exits.

            # Remove nonexistent files from uploaded file path list.
            state['uploaded_file_paths'] = [
                p for p in state['uploaded_file_paths']
                if (dir_path / p).exists()]

            # Remove nonexistent files from failed upload list.
            state['failed_uploads'] = deque(
                u for u in state['failed_uploads']
                if (dir_path / u['file_path']).exists())
            
            uploaded_file_paths = state['uploaded_file_paths']
            failed_uploads = state['failed_uploads']

            # Get paths of new files to upload.
            new_file_paths = self._get_new_file_paths(
                uploaded_file_paths, failed_uploads)

            for file_path in new_file_paths:

                # Stop if requested.
                if self._stop_event.is_set():
                    return

                # Upload file.
                if self._upload_file(file_path, 0):
                    # upload succeeded

                    uploaded_file_paths.append(file_path)
                    self._execute_post_upload_action(file_path)

                else:
                    # upload failed

                    # Append new failed upload to failed uploads list.
                    failed_uploads.append({
                        'file_path': file_path,
                        'failure_count': 1
                    })
                    return

            while len(failed_uploads) != 0:

                # Stop if requested.
                if self._stop_event.is_set():
                    return
                
                # Pop first failed upload from failed uploads list.
                failed_upload = failed_uploads.popleft()
                file_path = failed_upload['file_path']
                failure_count = failed_upload['failure_count']

                # Upload file.
                if self._upload_file(file_path, failure_count):
                    # upload succeeded

                    uploaded_file_paths.append(file_path)
                    self._execute_post_upload_action(file_path)

                else:
                    # upload failed

                    # Increment failure count.
                    failed_upload['failure_count'] += 1

                    # Append failed upload to failed uploads list. We
                    # move it from the front of the list to the end as
                    # part of a round-robin upload retry strategy. This
                    # strategy prevents the starvation of upload retries
                    # that can succeed by others that cannot. (As an
                    # example of an upload that can never succeed, I have
                    # seen corrupted files for which open attempts always
                    # fail.)
                    failed_uploads.append(failed_upload)
                    return
 

    def _get_new_file_paths(self, uploaded_file_paths, failed_uploads):

        dir_path = self._settings.dir_path

        # Get paths of all files in directory that match pattern, sorted
        # lexicographically and made relative to directory.
        file_paths = sorted(dir_path.glob(self._glob_pattern))
        file_paths = [p.relative_to(dir_path) for p in file_paths]

        failed_file_paths = (u['file_path'] for u in failed_uploads)
        old_file_paths = \
            frozenset(uploaded_file_paths) | frozenset(failed_file_paths)

        new_file_paths = [p for p in file_paths if p not in old_file_paths]
        
        return new_file_paths


    def _upload_file(self, rel_file_path, failure_count):

        s = self._settings

        # Get S3 object key for file.
        object_key = '/'.join(rel_file_path.parts)
        if s.s3_object_key_prefix is not None:
            object_key = f'{s.s3_object_key_prefix}/{object_key}'
  
        # Get absolute file path.
        abs_file_path = s.dir_path / rel_file_path

        # Get failure count text for log message.
        if failure_count == 0:
            failure_count_text = ''
        else:
            suffix = '' if failure_count == 1 else 's'
            failure_count_text = \
                f' (with {failure_count} previous upload failure{suffix})'
            
        # Log upload attempt.
        _logger.info(
            f'Uploading file "{abs_file_path}"{failure_count_text} to S3 '
            f'bucket "{s.s3_bucket_name}", object key "{object_key}"...')
        
        try:

            # Create new session for each upload to help ensure that
            # session timeouts will not be an issue.
            session = boto3.Session(profile_name=s.aws_profile_name)

            s3 = session.client('s3', config=self._boto_config)

            s3.upload_file(abs_file_path, s.s3_bucket_name, object_key)

            return True

        except Exception as e:
            # upload failed

            _logger.warning(
                f'Failed to upload file "{abs_file_path}" to S3 bucket '
                f'"{s.s3_bucket_name}", object key "{object_key}". '
                f'Exception message was: {e}')
            
            return False


    def _execute_post_upload_action(self, rel_file_path):
        
        if self._post_upload_action is not None:
        
            try:
                self._post_upload_action.execute(rel_file_path)

            except Exception as e:
            
                abs_file_path = self._settings.dir_path / rel_file_path

                _logger.warning(
                    f'Post-upload action for file "{abs_file_path}" raised '
                    f'exception. Exception message was: {e}')
            

def _get_absolute_path(path):
    if path.is_absolute():
        return path
    else:
        return Path.cwd() / path


def _create_glob_pattern(settings):
    if settings.search_recursively:
        return f'**/{settings.file_name_pattern}'
    else:
        return settings.file_name_pattern
    

def _create_boto_config(settings):
    return Config(
        retries={
            'mode': 'standard',
            'max_attempts': 5
        },
        read_timeout=settings.boto_read_timeout)


def _create_post_upload_action(settings):
    action_settings = settings.post_upload_action
    if action_settings is None:
        return None
    else:
        return post_upload_actions.create_action(
            action_settings, settings.dir_path)


class _UploaderState:


    def __init__(self, dir_path):
        self._file_path = Path(dir_path) / _STATE_FILE_NAME
        self._state = None


    def __enter__(self):

        if self._file_path.exists():

            try:
                with self._file_path.open('r') as file:
                    self._state = yaml_utils.load(file)

            except Exception as e:
                    
                _logger.warning(
                    f'Attempt to read uploader state file "{self._file_path}" '
                    f'raised exception. Will start with empty uploaded file '
                    f'list and empty failed upload list. Exception message '
                    f'was: {e}')
                
                self._state = _get_initial_uploader_state()

        else:

            _logger.info(
                f'Uploader state file "{self._file_path}" does not exist. '
                f'Will start with empty uploaded file list and empty failed '
                f'upload list. ')
            
            self._state = _get_initial_uploader_state()

        # Convert uploaded file paths from strings to `Path` objects.
        self._state['uploaded_file_paths'] = \
            [Path(p) for p in self._state['uploaded_file_paths']]
        
        # Convert failed upload file paths from strings to `Path` objects.
        for u in self._state['failed_uploads']:
            u['file_path'] = Path(u['file_path'])
        
        return self._state


    def __exit__(self, exc_type, exc_value, traceback):

        try:

            # Files are usually uploaded in order by path, but upload
            # failures can cause some to be uploaded out of order. Sort
            # the uploaded file paths to make the state file easier to
            # interpret. Note that we do *not* sort the failed uploads,
            # since that would interfere with our round-robin upload
            # retry strategy.
            self._state['uploaded_file_paths'].sort()

            # Convert uploaded file paths from `Path` objects to strings.
            self._state['uploaded_file_paths'] = \
                [str(p) for p in self._state['uploaded_file_paths']]
            
            # Convert failed uploads deque to list since `yaml_utils.dump`
            # does not support deques.
            self._state['failed_uploads'] = list(self._state['failed_uploads'])

            # Convert failed upload file paths from `Path` objects to strings.
            for u in self._state['failed_uploads']:
                u['file_path'] = str(u['file_path'])

            with self._file_path.open('w') as file:
                yaml_utils.dump(self._state, file)

        except Exception as e:
            _logger.warning(
                f'Attempt to write uploader state file "{self._file_path}" '
                f'raised exception. Will not write updated state. Exception '
                f'message was: {e}')


def _get_initial_uploader_state():
    return {
        'uploaded_file_paths': [],
        'failed_uploads': []
    }
