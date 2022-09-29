import asyncio


TEST_SEQUENCE_LENGTH = 256
TEST_SEQUENCE = bytearray(range(TEST_SEQUENCE_LENGTH))

READ_TEST_CASES = (
    (0, 2),
    (5, 3),
    (3, 4),
    (100, 5),
    (50, 6),
)

READ_ERROR_TEST_CASES = (
    (-1, 0),
    (TEST_SEQUENCE_LENGTH + 1, 0),
    (0, -1),
    (0, TEST_SEQUENCE_LENGTH + 1),
)


class ByteSequenceTests:

    """
    Mixin class for various byte sequence unit test classes.

    This class contains a set of unit tests that all `ByteSequence`
    implementations must pass. The tests are run on the byte sequence
    `self.seq`, which any subclass of this mixin must set in its
    initializer. `self.seq` must comprise the 256 bytes 00 through FF.

    This class is a mixin instead of a `TestCase` subclass to avoid
    a problem that would result because of the way the `unittest`
    test framework works. If this class were a `TestCase` subclass,
    the `unittest` test framework would try to instantiate it and
    run its `test_*` methods, which would not work. We only want
    the methods to be run on instances of subclasses of the mixin,
    and not on an instance of the mixin itself.
    """


    def test_length(self):
        self.assertEqual(len(self.seq), TEST_SEQUENCE_LENGTH)


    def test_get_length_async(self):
        asyncio.run(self._test_get_length_async())


    async def _test_get_length_async(self):
        length = await self.seq.get_length_async()
        self.assertEqual(length, TEST_SEQUENCE_LENGTH)


    def test_read(self):
        for start_index, length in READ_TEST_CASES:
            actual = self.seq.read(start_index, length)
            expected = TEST_SEQUENCE[start_index:start_index + length]
            self.assertEqual(actual, expected)


    def test_read_errors(self):
        for args in READ_ERROR_TEST_CASES:
            self.assert_raises(ValueError, self.seq.read, *args)


    def test_read_async(self):
        asyncio.run(self._test_read_async())


    async def _test_read_async(self):
        for start_index, length in READ_TEST_CASES:
            actual = await self.seq.read_async(start_index, length)
            expected = TEST_SEQUENCE[start_index:start_index + length]
            self.assertEqual(actual, expected)


    def test_read_async_errors(self):
        asyncio.run(self._test_read_async_errors())


    async def _test_read_async_errors(self):
        for args in READ_ERROR_TEST_CASES:
            await self.assert_raises_async(
                ValueError, self.seq.read_async, *args)
