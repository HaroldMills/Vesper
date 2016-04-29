from vesper.signal.signal import Signal


class ArraySignal(Signal):
    
    
    def __init__(
            self, name, samples, origin_time=0, origin_datetime=None,
            sample_rate=1.):
        
        sample_array_shape = samples.shape[1:]
        length = samples.shape[0]
        start_index = 0
        
        super(ArraySignal, self).__init__(
            name, samples.dtype, sample_array_shape, length, start_index,
            origin_time, origin_datetime, sample_rate)
        
        self._samples = samples


    def __getitem__(self, key):
        return self._samples.__getitem__(key)
