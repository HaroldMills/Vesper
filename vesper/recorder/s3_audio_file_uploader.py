import logging

import aioboto3

from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


_DEFAULT_AWS_PROFILE_NAME = 'default'
_DEFAULT_S3_OBJECT_KEY_PREFIX = 'recordings'
_DEFAULT_DELETE_SUCCESSFULLY_UPLOADED_FILES = False


class S3AudioFileUploader:


    name = 'S3 Audio File Uploader'


    @staticmethod
    def parse_settings(settings):

        aws_profile_name = settings.get(
            'aws_profile_name', _DEFAULT_AWS_PROFILE_NAME)
        
        s3_bucket_name = settings.get_required('s3_bucket_name')

        s3_object_key_prefix = settings.get(
            's3_object_key_prefix', _DEFAULT_S3_OBJECT_KEY_PREFIX)
        
        delete_successfully_uploaded_files = settings.get(
            'delete_successfully_uploaded_files',
            _DEFAULT_DELETE_SUCCESSFULLY_UPLOADED_FILES)
        
        return Bunch(
            aws_profile_name=aws_profile_name,
            s3_bucket_name=s3_bucket_name,
            s3_object_key_prefix=s3_object_key_prefix,
            delete_successfully_uploaded_files=
                delete_successfully_uploaded_files)


    def __init__(self, settings, file_path):
        self._settings = settings
        self._file_path = file_path


    async def run(self):
                
        s = self._settings

        file_name = self._file_path.name
        object_key = f'{s.s3_object_key_prefix}/{file_name}'
  
        _logger.info(
            f'Uploading audio file "{self._file_path}" to S3 bucket '
            f'"{s.s3_bucket_name}", object key "{object_key}"...')
        
        try:

            session = aioboto3.Session(profile_name=s.aws_profile_name)

            async with session.client('s3') as s3:
                await s3.upload_file(
                    self._file_path, s.s3_bucket_name, object_key)

        except Exception as e:
            # TODO: Consider reattempting failed uploads some number of times.
            _logger.warning(
                f'Could not upload audio file "{self._file_path}" to S3 '
                f'bucket "{s.s3_bucket_name}", object key "{object_key}". '
                f'Exception message was: {e}')
            
        else:

            _logger.info(
                f'Successfully uploaded audio file "{self._file_path}" '
                f'to S3 bucket "{s.s3_bucket_name}", object key '
                f'"{object_key}".')
            
            if s.delete_successfully_uploaded_files:

                _logger.info(
                    f'Deleting audio file "{self._file_path}" uploaded '
                    f'to S3...')
                
                try:
                    self._file_path.unlink()

                except Exception as e:
                    _logger.warning(
                        f'Could not delete audio file "{self._file_path}" '
                        f'uploaded to S3. Exception message was: {e}')
                    
                else:
                    _logger.info(
                        f'Successfully deleted audio file '
                        f'"{self._file_path}" uploaded to S3.')
