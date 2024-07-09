'''
An S3 file uploader takes a sequence of file paths as input and produces
no output.

For each input file, the uploader queues an *upload task* to run in an
async event loop on a *task runner* thread. The task re-enqueues itself
on failure. The task runner checks the queue once per second normally,
but only once per minute when there are failed tasks on it. The main
aim of the failure handling is to weather network outages gracefully.
'''


from queue import Queue, Empty
from threading import Thread
import asyncio
import logging
import time

import aioboto3

from vesper.recorder.processor import Processor
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


_DEFAULT_AWS_PROFILE_NAME = 'default'
_DEFAULT_S3_OBJECT_KEY_PREFIX = None
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
        
        delete_uploaded_files = settings.get(
            'delete_uploaded_files', _DEFAULT_DELETE_UPLOADED_FILES)

        return Bunch(
            aws_profile_name=aws_profile_name,
            s3_bucket_name=s3_bucket_name,
            s3_object_key_prefix=s3_object_key_prefix,
            delete_uploaded_files=delete_uploaded_files)
        
        
    def _start(self):
        pass


    def _process(self, input_item, finished):

        dir_path, file_path = input_item

        s = self.settings

        _logger.info(f'Submitting task to upload file "{file_path}" to S3...')
        
        task = _UploadTask(
            dir_path, file_path, s.aws_profile_name, s.s3_bucket_name,
            s.s3_object_key_prefix, s.delete_uploaded_files)
        
        _task_runner.enqueue_task(task)


    def get_status_tables(self):

        s = self._settings
        
        rows = (
            ('AWS Profile Name', s.aws_profile_name),
            ('S3 Bucket Name', s.s3_bucket_name),
            ('S3 Object Key Prefix', s.s3_object_key_prefix),
            ('Delete Uploaded Files', s.delete_uploaded_files))

        table = StatusTable(self.name, rows)

        return [table]


class _UploadTask:


    def __init__(
            self, dir_path, file_path, aws_profile_name, s3_bucket_name,
            s3_object_key_prefix, delete_uploaded_file):
        
        self._dir_path = dir_path
        self._file_path = file_path
        self._aws_profile_name = aws_profile_name
        self._s3_bucket_name = s3_bucket_name
        self._s3_object_key_prefix = s3_object_key_prefix
        self._delete_uploaded_file = delete_uploaded_file
        self._failure_count = 0


    async def run(self):

        # Get S3 object key for audio file.
        object_key = '/'.join(self._file_path.parts)
        if self._s3_object_key_prefix is not None:
            object_key = f'{self._s3_object_key_prefix}/{object_key}'
  
        # Get absolute audio file path.
        abs_file_path = self._dir_path / self._file_path

        if self._failure_count == 0:
            attempt_text = ''
        else:
            attempt_text = f' (attempt {self._failure_count + 1})'

        _logger.info(
            f'Uploading audio file "{abs_file_path}" to S3 bucket '
            f'"{self._s3_bucket_name}", object key "{object_key}"'
            f'{attempt_text}...')
        
        try:

            session = aioboto3.Session(profile_name=self._aws_profile_name)

            async with session.client('s3') as s3:
                await s3.upload_file(
                    abs_file_path, self._s3_bucket_name, object_key)

        except Exception as e:
            # upload failed

            _logger.warning(
                f'Failed to upload file "{abs_file_path}" to S3 bucket '
                f'"{self._s3_bucket_name}", object key "{object_key}"'
                f'{attempt_text}. Exception message was: {e}')
            
            self._failure_count += 1
            
            return False

        else:
            # upload succeeded

            if self._delete_uploaded_file:
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

    This thread runs asynchronous tasks that upload files to S3. It
    receives the tasks via a thread-safe FIFO queue. Each task attempts
    to upload one file. If the upload fails, the thread re-enqueues the
    task and sleeps for awhile. It also sleeps when the queue is empty.
    """


    # TODO: Arrange for orderly shutdown of this thread. That probably
    # means it shouldn't be a daemon thread. Perhaps there could be an
    # `Event` that it checks in its run loop to see if it should quit,
    # and the `Event` gets set during shutdown. The recorder wouldn't
    # know specifically about the `Event`, but it would notify each
    # processor class (or processor?) of shutdown, and the
    # `S3FileUploader` class would respond by setting the event.


    def __init__(self):
        super().__init__(daemon=True)
        self._normal_mode_sleep_period = 1        # seconds
        self._failure_mode_sleep_period = 60      # seconds
        self._tasks = Queue()


    def enqueue_task(self, task):
        self._tasks.put(task)


    def run(self):
        asyncio.run(self._run())


    async def _run(self):

        while True:

            try:
                task = self._tasks.get()

            except Empty:
                # no tasks to run

                # Sleep before checking queue again.
                time.sleep(self._normal_mode_sleep_period)

            else:
                # got a task to run

                # Run task.
                upload_succeeded = await task.run()

                if not upload_succeeded:
                    # upload failed

                    # Re-enqueue failed task to retry later.
                    self.enqueue_task(task)

                    # Sleep before checking queue again.
                    time.sleep(self._failure_mode_sleep_period)


# The one and only `_S3FileUploaderTaskRunner` of the Vesper Recorder.
_task_runner = _S3FileUploaderTaskRunner()
_task_runner.start()
