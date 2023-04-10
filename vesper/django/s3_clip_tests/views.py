"""
Django views for comparing different ways of reading AWS S3 clip files.

View                            Description
----                            -----------

s3-clip-test                    Sync view that reads files synchronously.

async-s3-clip-test              Async view that reads files asynchronously
                                on Django event loop.

sync-to-async-s3-clip-test      Sync view that reads files asynchronously
                                on one-off event loop.

Each view times how long it takes to read an S3 clip file `_CLIP_COUNT`
(see below) times, and displays the time in its response.
"""


import asyncio
import time

from django.http import HttpResponse
from django.views import View
from environs import Env
import aioboto3
import boto3


_env = Env()
_AWS_ACCESS_KEY_ID = _env('VESPER_AWS_ACCESS_KEY_ID', None)
_AWS_SECRET_ACCESS_KEY = _env('VESPER_AWS_SECRET_ACCESS_KEY', None)
_AWS_REGION_NAME = _env('VESPER_AWS_REGION_NAME', None)
_AWS_S3_CLIP_BUCKET_NAME = _env('VESPER_AWS_S3_CLIP_BUCKET_NAME', None)
_AWS_S3_CLIP_FOLDER_PATH = _env('VESPER_AWS_S3_CLIP_FOLDER_PATH', None)

if _AWS_S3_CLIP_FOLDER_PATH is None:
    _OBJECT_KEY_PREFIX = ''
else:
    _OBJECT_KEY_PREFIX = _AWS_S3_CLIP_FOLDER_PATH
    if not _OBJECT_KEY_PREFIX.endswith('/'):
        _OBJECT_KEY_PREFIX += '/'
_OBJECT_KEY_PREFIX += '000/002'

_FILE_NAMES = ('Clip 000 002 751.wav',)
_CLIP_COUNT = 20


# Synchronous view that reads several S3 clips one at a time.
class S3ClipTestView(View):


    def get(self, request):

        start_time = time.time()

        session = boto3.Session(
            aws_access_key_id=_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=_AWS_SECRET_ACCESS_KEY,
            region_name=_AWS_REGION_NAME)
        
        s3 = session.resource('s3')
        object_keys = [_get_s3_object_key(name) for name in _FILE_NAMES]
        data = [
            _get_s3_object_data(s3, object_keys[0])
            for _ in range(_CLIP_COUNT)]
        # data = [_get_s3_object_data(s3, key) for key in object_keys]

        end_time = time.time()
        elapsed_time = _p(f'{end_time - start_time:.1f}')

        return HttpResponse(
            '\n'.join([elapsed_time] + [_p(f'{len(d)}') for d in data]))


def _get_s3_object_key(file_name):
    return f'{_OBJECT_KEY_PREFIX}{file_name}'


def _get_s3_object_data(s3, object_key):
    obj = s3.Object(_AWS_S3_CLIP_BUCKET_NAME, object_key)
    result = obj.get()
    body = result['Body']
    data = body.read()
    return data


def _p(s):
    return '<p>' + s + '</p>'


# Asynchronous view that reads several S3 clips all at once.
class AsyncS3ClipTestView(View):

    async def get(self, request):

        start_time = time.time()

        data = await _get_s3_objects()

        end_time = time.time()
        elapsed_time = _p(f'{end_time - start_time:.1f}')

        return HttpResponse(
            '\n'.join([elapsed_time] + [_p(f'{len(d)}') for d in data]))


async def _get_s3_objects():

    object_keys = [_get_s3_object_key(name) for name in _FILE_NAMES]
    object_key = object_keys[0]

    session = aioboto3.Session(
        aws_access_key_id=_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=_AWS_SECRET_ACCESS_KEY,
        region_name=_AWS_REGION_NAME)
    
    async with session.resource('s3') as s3:
        coroutines = [
            _get_s3_object_data_async(s3, object_key)
            for _ in range(_CLIP_COUNT)]
        return await asyncio.gather(*coroutines)


async def _get_s3_object_data_async(s3, object_key):
    obj = await s3.Object(_AWS_S3_CLIP_BUCKET_NAME, object_key)
    result = await obj.get()
    body = result['Body']
    data = await body.read()
    return data


# Synchronous view that runs a one-off event loop to read several
# S3 clips all at once.
class SyncToAsyncS3ClipTestView(View):

    def get(self, request):

        start_time = time.time()

        data = asyncio.run(_get_s3_objects())

        end_time = time.time()
        elapsed_time = _p(f'{end_time - start_time:.1f}')

        return HttpResponse(
            '\n'.join([elapsed_time] + [_p(f'{len(d)}') for d in data]))
