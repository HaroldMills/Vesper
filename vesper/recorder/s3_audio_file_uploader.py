import logging

import aioboto3

from vesper.recorder.audio_file_processor import AudioFileProcessor
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


_DEFAULT_AWS_PROFILE_NAME = 'default'
_DEFAULT_S3_OBJECT_KEY_PREFIX = 'recordings'


class S3AudioFileUploader(AudioFileProcessor):


    type_name = 'S3 Audio File Uploader'


    @staticmethod
    def parse_settings(settings):

        aws_profile_name = settings.get(
            'aws_profile_name', _DEFAULT_AWS_PROFILE_NAME)
        
        s3_bucket_name = settings.get_required('s3_bucket_name')

        s3_object_key_prefix = settings.get(
            's3_object_key_prefix', _DEFAULT_S3_OBJECT_KEY_PREFIX)
        
        return Bunch(
            aws_profile_name=aws_profile_name,
            s3_bucket_name=s3_bucket_name,
            s3_object_key_prefix=s3_object_key_prefix)


    async def process_file(self, recording_dir_path, audio_file_path):

        s = self._settings

        # Get S3 object key for audio file.
        s3_audio_file_path = '/'.join(audio_file_path.parts)
        object_key = f'{s.s3_object_key_prefix}/{s3_audio_file_path}'
  
        # Get absolute audio file path.
        abs_file_path = recording_dir_path / audio_file_path

        _logger.info(
            f'Uploading audio file "{abs_file_path}" to S3 bucket '
            f'"{s.s3_bucket_name}", object key "{object_key}"...')
        
        try:

            session = aioboto3.Session(profile_name=s.aws_profile_name)

            async with session.client('s3') as s3:

                await s3.upload_file(
                    abs_file_path, s.s3_bucket_name, object_key)

        except Exception as e:
            # TODO: Consider reattempting failed uploads some number of times.
            _logger.warning(
                f'Could not upload audio file "{abs_file_path}" to S3 '
                f'bucket "{s.s3_bucket_name}", object key "{object_key}". '
                f'Exception message was: {e}')


    def get_status_tables(self):

        s = self._settings
        
        rows = (
            ('AWS Profile Name', s.aws_profile_name),
            ('S3 Bucket Name', s.s3_bucket_name),
            ('S3 Object Key Prefix', s.s3_object_key_prefix)
        )

        table = Bunch(title=self.name, rows=rows)

        return [table]
