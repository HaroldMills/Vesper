'''
An S3 file uploader takes a sequence of file paths as input and produces
no output.

For each input file, the uploader queues an asynchronous upload task.
If the upload fails, the task adds the file to a *retry queue*. A
*retry thread* periodically checks the queue and attempts to upload
the queued files. It sleeps after either uploading all of the queued
files or on the first failure. It should probably move a file for which
uploading fails to the back of the queue to avoid starving files queued
behind it. The basic idea here is to make a reasonable effort to recover
from brief network outages.
'''


import logging

import aioboto3

from vesper.recorder.processor import Processor
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch
import vesper.recorder.async_task_thread as async_task_thread


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
        
        async_task_thread.instance.submit(task)


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


    async def run(self):

        # Get S3 object key for audio file.
        object_key = '/'.join(self._file_path.parts)
        if self._s3_object_key_prefix is not None:
            object_key = f'{self._s3_object_key_prefix}/{object_key}'
  
        # Get absolute audio file path.
        abs_file_path = self._dir_path / self._file_path

        _logger.info(
            f'Uploading audio file "{abs_file_path}" to S3 bucket '
            f'"{self._s3_bucket_name}", object key "{object_key}"...')
        
        try:

            session = aioboto3.Session(profile_name=self._aws_profile_name)

            async with session.client('s3') as s3:
                await s3.upload_file(
                    abs_file_path, self._s3_bucket_name, object_key)

        except Exception as e:
            # upload failed

            _logger.warning(
                f'Failed to upload file "{abs_file_path}" to S3 bucket '
                f'"{self._s3_bucket_name}", object key "{object_key}". '
                f'Exception message was: {e}')
            
            # TODO: Retry failed uploads.

        else:
            # upload succeeded
       
            if self._delete_uploaded_file:
                self._delete_file(abs_file_path)
                self._delete_empty_ancestor_dirs()


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
