from logging.handlers import QueueHandler
from multiprocessing import Process, Queue
import logging
import time

from botocore.client import Config
import boto3

import vesper.recorder.error_utils as error_utils


_LOGGING_LEVEL = logging.INFO


class S3FileUploaderProcess(Process):


    """
    S3 file uploader task runner.

    This process runs tasks that upload files to S3. It receives the tasks
    via a multiprocessing FIFO queue. Each task attempts to upload one file.
    During normal operation, a task arrives in the queue periodically and
    the uploader runs it to upload the specified file. If an upload fails
    and retries are enabled, the task runner re-enqueues the task and
    sleeps for awhile before resuming reading tasks from the queue and
    running them. If an upload fails and retries are not enabled, the task
    runner discards the task.
    """


    def __init__(
            self, retry_failed_uploads, upload_failure_pause_duration,
            logging_queue):
        
        super().__init__(daemon=True)
        self._retry_failed_uploads = retry_failed_uploads
        self._upload_failure_pause_duration = upload_failure_pause_duration
        self._logging_queue = logging_queue
        self._tasks = Queue()


    def enqueue_task(self, task):
        self._tasks.put(task)


    def run(self):

        try:

            self._configure_logging()

            while True:

                # Get next file upload task.
                task = self._tasks.get()

                if task is None:
                    # time to quit

                    self._logger.info(
                        f'S3 file uploader task runner quitting...')
                    break

                else:
                    # got task to run

                    # Run task.
                    upload_succeeded = task.run()

                    if not upload_succeeded:

                        if self._retry_failed_uploads:

                            # Re-enqueue failed task to retry later.
                            self.enqueue_task(task)

                        # Pause before getting next task.
                        time.sleep(self._upload_failure_pause_duration)

        except KeyboardInterrupt:
            pass

        except Exception:
            error_utils.handle_top_level_exception(
                'S3 file uploader task runner process')


    def _configure_logging(self):
        
        # Get the root logger for this process.
        logger = logging.getLogger()

        # Add handler to root logger that forwards all log messages to
        # the logging process.
        handler = QueueHandler(self._logging_queue)
        logger.addHandler(handler)
        # if len(logger.handlers) == 0:
        #     logger.addHandler(handler)

        print(f'S3FileUploaderProcess._configure_logging: {logger.handlers}')

        # Set logging level for this process.
        logger.setLevel(_LOGGING_LEVEL)

        # Get the logger for this module.
        self._logger = logging.getLogger(__name__)


class S3FileUploaderTask:


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

        # Get the logger for this module.
        self._logger = logging.getLogger(__name__)

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

        self._logger.info(
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

            self._logger.warning(
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

        self._logger.info(f'Deleting file "{file_path}" uploaded to S3...')
        
        try:
            file_path.unlink()

        except Exception as e:
            self._logger.warning(
                f'Could not delete file "{file_path}" uploaded to S3. '
                f'Exception message was: {e}')
            

    def _delete_empty_ancestor_dirs(self):

        """
        Deletes the directories of `self._file_path.parents[:-1]`
        up until the first non-empty directory. Does not consider
        `self._file_path.parents[-1]` since it is always '.'.
        """


        if self._file_path.is_absolute():

            self._logger.error(
                f'Internal Vesper Recorder error: encountered absolute '
                f'file path "{self._file_path}" when deleting empty '
                f'ancestor directories in S3 file uploader task. Expected '
                f'a relative path. No directories will be deleted.')
            
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

                self._logger.warning(
                    f'Deleting empty directory "{abs_dir_path}"...')
                    
                try:
                    abs_dir_path.rmdir()

                except Exception as e:
                    self._logger.warning(
                        f'Could not delete empty directory "{abs_dir_path}". '
                        f'Error message was: {e}')
                    
            else:
                # directory not empty

                # We can stop here, since any further directories will
                # be ancestors of this one and hence not empty either.
                break
