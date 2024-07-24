'''
An S3 file uploader takes a sequence of file paths as input and produces
no output.

For each input file, the uploader queues an *upload task* to run on a
*task runner* thread. There is one task runner thread per S3 file
uploader. The task runner thread reads upload tasks from its queue and
runs them. If a task fails and retries are enabled, the task runner
re-enqueues it and pauses for the *retry pause duration* before getting
and running the next task from its queue. If a task fails and retries
are not enabled, the task runner discards it. The main aim of the task
runner's failure handling is to weather network outages gracefully,
retrying uploads at the rate determined by the retry pause duration
until an upload succeeds and then resuming normal operation.
'''


from queue import Queue
from threading import Thread
import logging
import time

from botocore.client import Config
import boto3

from vesper.recorder.processor import Processor
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


_DEFAULT_AWS_PROFILE_NAME = 'default'
_DEFAULT_S3_OBJECT_KEY_PREFIX = None
_DEFAULT_BOTO_READ_TIMEOUT = 300                # seconds
_DEFAULT_RETRY_FAILED_UPLOADS = True
_DEFAULT_UPLOAD_FAILURE_PAUSE_DURATION = 60     # seconds
_DEFAULT_DELETE_UPLOADED_FILES = False


_logger = logging.getLogger(__name__)


class S3FileUploader(Processor):


    type_name = 'S3 File Uploader'


    @staticmethod
    def parse_settings(settings):

        aws_profile_name = settings.get(
            'aws_profile_name', _DEFAULT_AWS_PROFILE_NAME)
        
        s3_bucket_name = settings.get_required('s3_bucket_name')

        s3_object_key_prefix = settings.get(
            's3_object_key_prefix', _DEFAULT_S3_OBJECT_KEY_PREFIX)
        
        boto_read_timeout = settings.get(
            'boto_read_timeout', _DEFAULT_BOTO_READ_TIMEOUT)
        
        retry_failed_uploads = settings.get(
            'retry_failed_uploads', _DEFAULT_RETRY_FAILED_UPLOADS)
        
        upload_failure_pause_duration = settings.get(
            'upload_failure_pause_duration',
            _DEFAULT_UPLOAD_FAILURE_PAUSE_DURATION)
        
        delete_uploaded_files = settings.get(
            'delete_uploaded_files', _DEFAULT_DELETE_UPLOADED_FILES)

        return Bunch(
            aws_profile_name=aws_profile_name,
            s3_bucket_name=s3_bucket_name,
            s3_object_key_prefix=s3_object_key_prefix,
            boto_read_timeout=boto_read_timeout,
            retry_failed_uploads=retry_failed_uploads,
            upload_failure_pause_duration=upload_failure_pause_duration,
            delete_uploaded_files=delete_uploaded_files)
        
        
    def _start(self):

        s = self._settings

        self._task_runner = _S3FileUploaderTaskRunner(
            s.retry_failed_uploads, s.upload_failure_pause_duration)
        
        self._task_runner.start()


    def _process(self, input_item, finished):
        dir_path, file_path = input_item
        _logger.info(f'Submitting task to upload file "{file_path}" to S3...')
        task = _UploadTask(dir_path, file_path, self.settings)
        self._task_runner.enqueue_task(task)


    def get_status_tables(self):

        s = self._settings
        
        rows = (
            ('AWS Profile Name', s.aws_profile_name),
            ('S3 Bucket Name', s.s3_bucket_name),
            ('S3 Object Key Prefix', s.s3_object_key_prefix),
            ('Boto Read Timeout (seconds)', s.boto_read_timeout),
            ('Retry Failed Uploads', s.retry_failed_uploads),
            ('Upload Failure Pause Duration (seconds)',
             s.upload_failure_pause_duration),
            ('Delete Uploaded Files', s.delete_uploaded_files))

        table = StatusTable(self.name, rows)

        return [table]


class _UploadTask:


    def __init__(self, dir_path, file_path, settings):

        self._dir_path = dir_path
        self._file_path = file_path
        self._settings = settings

        self._boto_config = Config(
            retries={
                'mode': 'standard',
                'max_attempts': 5
            },
            read_timeout=self._settings.boto_read_timeout)

        self._failure_count = 0


    def run(self):

        s = self._settings

        # Get S3 object key for audio file.
        object_key = '/'.join(self._file_path.parts)
        if s.s3_object_key_prefix is not None:
            object_key = f'{s.s3_object_key_prefix}/{object_key}'
  
        # Get absolute audio file path.
        abs_file_path = self._dir_path / self._file_path

        if self._failure_count == 0:
            attempt_text = ''
        else:
            attempt_text = f' (attempt {self._failure_count + 1})'

        _logger.info(
            f'Uploading audio file "{abs_file_path}" to S3 bucket '
            f'"{s.s3_bucket_name}", object key "{object_key}"'
            f'{attempt_text}...')
        
        try:

            # Create new session for each upload to ensure that session
            # timeouts will not be an issue.
            session = boto3.Session(profile_name=s.aws_profile_name)

            s3 = session.client('s3', config=self._boto_config)

            s3.upload_file(abs_file_path, s.s3_bucket_name, object_key)

        except Exception as e:
            # upload failed

            _logger.warning(
                f'Failed to upload file "{abs_file_path}" to S3 bucket '
                f'"{s.s3_bucket_name}", object key "{object_key}"'
                f'{attempt_text}. Exception message was: {e}')
            
            self._failure_count += 1
            
            return False

        else:
            # upload succeeded

            if s.delete_uploaded_files:
                self._delete_file(abs_file_path)
                self._delete_empty_ancestor_dirs()

            return True


    def _delete_file(self, file_path):

        _logger.info(f'Deleting file "{file_path}" uploaded to S3...')
        
        try:
            file_path.unlink()

        except Exception as e:
            _logger.warning(
                f'Could not delete file "{file_path}" uploaded to S3. '
                f'Exception message was: {e}')
            

    def _delete_empty_ancestor_dirs(self):

        """
        Deletes the directories of `self._file_path.parents[:-1]`
        up until the first non-empty directory. Does not consider
        `self._file_path.parents[-1]` since it is always '.'.
        """


        if self._file_path.is_absolute():

            _logger.error(
                f'Internal Vesper Recorder error: encountered absolute '
                f'file path "{self._file_path}" when deleting empty '
                f'ancestor directories in S3 file uploader. Expected a '
                f'relative path. No directories will be deleted.')
            
            return
            
        for rel_dir_path in self._file_path.parents[:-1]:

            # We could just invoke `dir_path.rmdir` instead of checking
            # if the directory is empty first, and ignore any exception
            # that it raises. That should work, deleting an empty
            # directory and doing nothing for a non-empty one. Even so,
            # I am uncomfortable with the idea of invoking `rmdir` on
            # directories that I know I don't want to delete, counting
            # on that method to protect me from disaster. It also
            # wouldn't allow us to detect failed attempts to delete
            # empty directories.

            abs_dir_path = self._dir_path / rel_dir_path

            child_paths = tuple(abs_dir_path.iterdir())

            if len(child_paths) == 0:
                # directory empty

                _logger.warning(
                    f'Deleting empty directory "{abs_dir_path}"...')
                    
                try:
                    abs_dir_path.rmdir()

                except Exception as e:
                    _logger.warning(
                        f'Could not delete empty directory "{abs_dir_path}". '
                        f'Error message was: {e}')
                    
            else:
                # directory not empty

                # We can stop here, since any further directories will
                # be ancestors of this one and hence not empty either.
                break


class _S3FileUploaderTaskRunner(Thread):


    """
    S3 file uploader task runner.

    This thread runs tasks that upload files to S3. It receives the tasks
    via a thread-safe FIFO queue. Each task attempts to upload one file.
    During normal operation, a task arrives in the queue periodically and
    the uploader runs it to upload the specified file. If an upload fails
    and retries are enabled, the thread re-enqueues the task and sleeps
    for awhile before resuming reading tasks from the queue and running
    them. If an upload fails and retries are not enabled, the task
    runner discards the task.
    """


    # TODO: Arrange for orderly shutdown of this thread. That probably
    # means it shouldn't be a daemon thread. Perhaps a value of `None`
    # in the task queue could signal that it's time to shut down.


    def __init__(self, retry_failed_uploads, upload_failure_pause_duration):
        super().__init__(daemon=True)
        self._retry_failed_uploads = retry_failed_uploads
        self._upload_failure_pause_duration = upload_failure_pause_duration
        self._tasks = Queue()


    def enqueue_task(self, task):
        self._tasks.put(task)


    def run(self):

        while True:

            # Get next file upload task.
            task = self._tasks.get()

            # Run task.
            upload_succeeded = task.run()

            if not upload_succeeded:

                if self._retry_failed_uploads:

                    # Re-enqueue failed task to retry later.
                    self.enqueue_task(task)

                # Pause before getting next task.
                time.sleep(self._upload_failure_pause_duration)
