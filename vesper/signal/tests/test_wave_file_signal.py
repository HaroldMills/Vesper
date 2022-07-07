from pathlib import Path

from vesper.signal.signal_error import SignalError
from vesper.signal.tests.signal_test_case import SignalTestCase
from vesper.signal.time_axis import TimeAxis
from vesper.signal.wave_file_signal import WaveFileSignal
import vesper.signal.tests.utils as utils
import vesper.tests.test_utils as test_utils


_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))


class WaveFileSignalTests(SignalTestCase):


    def test_init(self):
        
        cases = [
            ('Header Only.wav', 0, 1, 24000, '<i2'),
            ('One Channel.wav', 10, 1, 22050, '<i2'),
            ('Two Channels.wav', 10, 2, 24000, '<i2')
        ]
        
        for (file_name, frame_count, channel_count, frame_rate, dtype) in \
                cases:
            
            file_path = _DATA_DIR_PATH / file_name
            time_axis = TimeAxis(frame_count, frame_rate)
            shape = (channel_count, frame_count)
            samples = utils.create_samples(shape, dtype='<i2')
            
            signal = WaveFileSignal(file_path, name=file_name)
            self.assert_signal(
                signal, file_name, time_axis, channel_count, (), dtype,
                samples)
            
            signal = WaveFileSignal(file_path)
            self.assert_signal(
                signal, 'Signal', time_axis, channel_count, (), dtype,
                samples)

            with WaveFileSignal(file_path) as signal:
                self.assertTrue(signal.is_open)
                self.assert_signal(
                    signal, 'Signal', time_axis, channel_count, (), dtype,
                    samples)

            self.assertFalse(signal.is_open)


    def test_nonexistent_file_error(self):
        file_path = _DATA_DIR_PATH / 'Nonexistent'
        self.assert_raises(SignalError, WaveFileSignal, file_path)


    def test_nonfile_error(self):
        file_path = _DATA_DIR_PATH / 'Directory'
        self.assert_raises(SignalError, WaveFileSignal, file_path)


    def test_non_wav_file_error(self):
        file_path = _DATA_DIR_PATH / 'Empty'
        self.assert_raises(SignalError, WaveFileSignal, file_path)
        
        
    def test_empty_wav_file_error(self):
        file_path = _DATA_DIR_PATH / 'Empty.wav'
        self.assert_raises(SignalError, WaveFileSignal, file_path)


    def test_closed_wav_file_read_error(self):
        file_path = _DATA_DIR_PATH / 'One Channel.wav'
        signal = WaveFileSignal(file_path)
        signal.close()
        self.assert_raises(SignalError, signal.as_frames.__getitem__, 0)

        
    def test_truncated_file_read_error(self):
        file_path = _DATA_DIR_PATH / 'Truncated.wav'
        signal = WaveFileSignal(file_path)
        time_axis = TimeAxis(10, 22050)
        self.assert_signal(signal, 'Signal', time_axis, 1, (), '<i2')
        self.assert_raises(SignalError, lambda s: s.as_channels[0], signal)
