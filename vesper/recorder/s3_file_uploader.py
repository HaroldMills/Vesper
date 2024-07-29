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


import logging

from vesper.recorder.processor import Processor
from vesper.recorder.s3_file_uploader_process import (
    S3FileUploaderProcess, S3FileUploaderTask)
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch
import vesper.recorder.multiprocess_logging as multiprocess_logging


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

        self._uploader_process = S3FileUploaderProcess(
            s.retry_failed_uploads, s.upload_failure_pause_duration,
            multiprocess_logging.logging_queue)
        
        self._uploader_process.start()


    def _process(self, input_item, finished):

        dir_path, file_path = input_item

        _logger.info(
            f'Processor "{self.name}" submitting task to upload file '
            f'"{file_path}" to S3...')

        task = S3FileUploaderTask(dir_path, file_path, self.settings)
        self._uploader_process.enqueue_task(task)

        if finished:

            _logger.info(
                f'Processor "{self.name}" signaling task runner to quit...')
            
            self._uploader_process.enqueue_task(None)


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
