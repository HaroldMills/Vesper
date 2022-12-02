"""Module containing class `S3ByteSequence`."""


import aioboto3

from vesper.signal.byte_sequence import ByteSequence


class S3ByteSequence(ByteSequence):

    """Wraps an AWS S3 object as a `ByteSequence`."""


    def __init__(self, region_name, bucket_name, object_key):

        super().__init__()
        
        self._region_name = region_name
        self._bucket_name = bucket_name
        self._object_key = object_key

        self._session = None
        self._s3_resource = None
        self._s3 = None
        self._object = None


    @property
    def region_name(self):
        return self._region_name


    @property
    def bucket_name(self):
        return self._bucket_name


    @property
    def object_key(self):
        return self._object_key


    @property
    def inside(self):
        return self._object is not None


    async def _get_length(self):
        return await self._object.content_length


    async def __aenter__(self):
        if not self.inside:
            self._session = aioboto3.Session(region_name=self._region_name)
            self._s3_resource = self._session.resource('s3')
            self._s3 = await self._s3_resource.__aenter__()
            self._object = \
                await self._s3.Object(self._bucket_name, self._object_key)
        return self


    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.inside:
            self._object = None
            self._s3 = None
            await self._s3_resource.__aexit__(exc_type, exc_value, traceback)
            self._s3_resource = None
            self._session = None


    async def _read(self, start_offset, length):
        end_offset = start_offset + length - 1
        range = f'bytes={start_offset}-{end_offset}'
        result = await self._object.get(Range=range)
        body = result['Body']
        bytes = await body.read()
        return bytes
