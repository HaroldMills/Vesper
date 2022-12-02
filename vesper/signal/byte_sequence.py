"""Module containing class `ByteSequence`."""


class ByteSequence:

    """
    A finite, immutable sequence of bytes that is accessed asynchronously.
    """


    def __init__(self):
        self._length = None


    @property
    def inside(self):
        return False


    async def get_length(self):
        self._check_if_inside()
        if self._length is None:
            self._length = await self._get_length()
        return self._length


    def _check_if_inside(self):
        if not self.inside:
            raise ByteSequenceError(
                'Attempt to use byte sequence without first entering it.')


    async def _get_length(self):
        raise NotImplementedError()


    async def read(self, start_index, length):
        seq_length = await self.get_length()
        self._check_read_args(start_index, length, seq_length)
        return await self._read(start_index, length)


    def _check_read_args(self, start_index, read_length, seq_length):

        if start_index < 0:
            raise ValueError(
                f'Bad byte sequence read start index {start_index}. '
                f'Start index must be at least zero.')

        if start_index > seq_length:
            raise ValueError(
                f'Bad byte sequence read start index {start_index}. '
                f'Start index must be at most sequence length {seq_length}.')

        if read_length < 0:
            raise ValueError(
                f'Bad byte sequence read length {read_length}. '
                f'Length must be at least zero.')

        end_index = start_index + read_length

        if end_index > seq_length:
            raise ValueError(
                f'Bad byte sequence read arguments {start_index} and '
                f'{read_length}. Specified read segment [{start_index}, '
                f'{end_index}) extends past end of sequence of length '
                f'{seq_length}.')
                

    async def _read(self, start_index, length):
        raise NotImplementedError()


class ByteSequenceError(Exception):
    pass
