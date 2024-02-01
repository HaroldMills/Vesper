class AudioSampleFormat:


    def __init__(self, name, sample_size, min_sample, max_sample):
        self._name = name
        self._sample_size = sample_size
        self._min_sample = min_sample
        self._max_sample = max_sample
        self._max_abs_sample = max(abs(min_sample), abs(max_sample))


    @property
    def name(self):
        return self._name
    
    
    @property
    def sample_size(self):

        """the sample size, in bytes."""

        return self._sample_size
    

    @property
    def min_sample(self):
        return self._min_sample
    

    @property
    def max_sample(self):
        return self._max_sample
    

    @property
    def max_abs_sample(self):
        return self._max_abs_sample
    

    def get_raw_sample_data(self, samples):

        """
        Gets raw sample data corresponding to the specified samples.

        Parameters
        ----------
        samples : 2-D NumPy array with shape (channel_count, frame_count)
            the samples for which to get raw data. The array does not have
            to have any particular dtype, but the samples must be within
            range for this sample format.

        Returns
        -------
        bytes
            a raw data version of `samples`. In this version, each sample
            is formatted according to this `AudioSampleFormat` and the
            samples of the different channels of a sample frame are
            interleaved.
        """

        raise NotImplementedError()
    

    def normalize_samples(self, samples):

        """
        Gets a normalized version of the specified samples.

        Signed integer sample formats normalize samples by dividing
        them by the maximum absolute sample value (i.e. the
        `max_abs_sample` attribute of the format) to put them in
        the range [-1, 1].
        
        Floating point sample formats normalize samples by converting
        them to the float32 dtype if needed. They perform no scaling,
        however, assuming that the samples are already in the range
        [-1, 1].

        Parameters
        ----------
        samples : NumPy array
            the samples to normalize. The array does not have to have
            a particular number of dimensions or dtype.

        Returns
        -------
        float32 NumPy array
            a normalized version of `samples`.
        """

        raise NotImplementedError()

    
class Int16AudioSampleFormat(AudioSampleFormat):


    def __init__(self):
        super().__init__('int16', 2, -32768, 32767)


    def get_raw_sample_data(self, samples):
        return samples.astype('int16').transpose().tobytes()
    

    def normalize_samples(self, samples):
        return samples.astype('float32') / self.max_abs_sample


AUDIO_SAMPLE_FORMATS = {
    f.name: f for f in (
        Int16AudioSampleFormat(),
    )
}
