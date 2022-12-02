"""Module containing class `FileByteSequence`."""


from vesper.signal.byte_sequence import ByteSequence, ByteSequenceError


class FileByteSequence(ByteSequence):

    """Wraps a disk file as a `ByteSequence`."""


    def __init__(self, path):

        super().__init__()
        
        self._check_path(path)

        self._path = path
        self._file = None
        self._pos = None


    def _check_path(self, path):

        if not path.exists():
            raise ValueError(f'Path "{path}" does not exist.')

        if not path.is_file():
            raise ValueError(f'Path "{path}" is not a file.')


    @property
    def path(self):
        return self._path


    @property
    def inside(self):
        return self._file is not None


    async def _get_length(self):
        return self._path.stat().st_size


    async def __aenter__(self):
        if not self.inside:
            self._file = open(self._path, 'rb')
            self._pos = 0
        return self


    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.inside:
            self._file.close()
            self._file = None
            self._pos = None


    async def _read(self, start_index, length):

        if self._pos != start_index:
            self._file.seek(start_index)

        bytes = self._file.read(length)

        if len(bytes) != length:
            raise ByteSequenceError(
                f'File read failed. Got {len(bytes)} bytes instead of '
                f'requested {length}.')

        self._pos = start_index + length

        return bytes
