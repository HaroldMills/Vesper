from pathlib import Path
import asyncio
import time

from botocore.client import Config
from botocore.exceptions import ClientError
import aioboto3
import boto3


DATA_DIR_PATH = Path('/Users/harold/Desktop/NFC/Data/S3 Upload Test Files')
FILE_NAME = '1.00.wav'
AWS_PROFILE_NAME = 'harold-harold'
BUCKET_NAME = 'vesper-test'
OBJECT_KEY_PREFIX = 'uploads'
BOTO_CONFIG = Config(
    retries={
        'mode': 'standard',
        'max_attempts': 5},
    read_timeout=300)


def main():
    file_path = DATA_DIR_PATH / FILE_NAME
    object_key = f'{OBJECT_KEY_PREFIX}/{FILE_NAME}'
    # upload_file_to_s3(file_path, object_key)
    upload_file_to_s3_async(file_path, object_key)


def upload_file_to_s3(file_path, object_key):
    print(f'Uploading file "{file_path.name}" to S3...')
    start_time = time.time()
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, BUCKET_NAME, object_key)
    except ClientError as e:
        duration = get_duration(start_time)
        print(f'Upload failed after {duration:.1f} seconds with message: {e}')
    else:
        duration = get_duration(start_time)
        print(f'Upload succeeded and took {duration:.1f} seconds.')


def get_duration(start_time):
    return time.time() - start_time


def upload_file_to_s3_async(file_path, object_key):
    coroutine = upload_file_to_s3_async_aux(file_path, object_key)
    asyncio.run(coroutine)


async def upload_file_to_s3_async_aux(file_path, object_key):

    print(f'Uploading file "{file_path.name}" to S3...')
    start_time = time.time()
    session = aioboto3.Session(profile_name=AWS_PROFILE_NAME)
    try:
        async with session.client('s3', config=BOTO_CONFIG) as s3:
            await s3.upload_file(file_path, BUCKET_NAME, object_key)
    except Exception as e:
        duration = get_duration(start_time)
        print(f'Upload failed after {duration:.1f} seconds with message: {e}')
        raise
    else:
        duration = get_duration(start_time)
        print(f'Upload succeeded and took {duration:.1f} seconds.')


if __name__ == '__main__':
    main()
