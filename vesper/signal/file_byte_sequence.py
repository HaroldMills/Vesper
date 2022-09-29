"""Module containing class `FileByteSequence`."""


from vesper.signal.byte_sequence import ByteSequence, ByteSequenceError


class FileByteSequence(ByteSequence):

    """Wraps a disk file as a `ByteSequence`."""


    def __init__(self, path):

        super().__init__()
        
        self._check_path(path)

        self._path = path
        self._length = None
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


    def _get_length(self):
        return self._path.stat().st_size


    def open(self):
        if self._file is None:
            self._file = open(self._path, 'rb')
            self._pos = 0


    @property
    def is_open(self):
        return self._file is not None


    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
            self._pos = None


    def __enter__(self):
        self.open()
        return self
     

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()


    def _read(self, start_index, length):

        if self._file is None:
            # file not open

            with self:
                self._file.seek(start_index)
                return self._read_aux(length)

        else:
            # file open

            if self._pos != start_index:
                self._file.seek(start_index)

            bytes = self._read_aux(length)
            self._pos = start_index + length
            return bytes


    def _read_aux(self, length):

        bytes = self._file.read(length)

        if len(bytes) != length:
            raise ByteSequenceError(
                f'File read failed. Got {len(bytes)} bytes instead of '
                f'requested {length}.')

        return bytes
