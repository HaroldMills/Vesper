from pprint import pprint
import itertools

import sounddevice as sd


SAMPLE_RATES = (
    16000, 22050, 24000, 24001, 32000, 44100, 48000, 88200, 96000, 176400,
    192000)

SAMPLE_DTYPES = ('int16', 'int24', 'int32', 'float32')

TEST_RECORDING_DEVICE_INDEX = 1
TEST_RECORDING_CHANNEL_COUNT = 1
TEST_RECORDING_SAMPLE_RATE = 24000
TEST_RECORDING_SAMPLE_DTYPE = 'int16'
TEST_RECORDING_DURATION = .1


def main():

    show_host_apis()
    show_devices()
    test_recording()


def show_host_apis():

    print('Host APIs:')

    apis = sd.query_hostapis()

    for i, api in enumerate(apis):
        print(f'{i}:')
        pprint(api)
        print()

    print(f'Default host API index: {sd.default.hostapi}')
    print()


def show_devices():

    print('Devices:')

    devices = sd.query_devices()

    for i, device in enumerate(devices):

        print(f'{i}:')
        pprint(device)
        print()

        show_supported_input_settings(device)
       

    print(f'Default device indices: {sd.default.device}')
    print()


def show_defaults():
    default = sd.default
    print(f'default device: {default.device}')
    print(f'default channels: {default.channels}')
    print(f'default dtype: {default.dtype}')
    print(f'default extra settings: {default.extra_settings}')
    print(f'default sample rate: {default.samplerate}')
    print()
    

def show_supported_input_settings(device):

    channel_counts = tuple(range(1, device['max_input_channels'] + 1))

    if len(channel_counts) == 0:
        return
    
    device_index = device['index']

    print(f'Input setting support for device {device_index}:')

    all_settings = \
        itertools.product(channel_counts, SAMPLE_RATES, SAMPLE_DTYPES)
    
    for settings in all_settings:
        result = are_input_settings_supported(device_index, *settings)
        print(f'    {settings} {result}')

    print()


def are_input_settings_supported(
        device_index, channel_count, sample_rate, sample_dtype):
    
    try:
        sd.check_input_settings(
            device_index, channels=channel_count, dtype=sample_dtype,
            samplerate=sample_rate)
        
    except:
        return False
    
    return True


def test_recording():

    print('Testing recording...')
    
    frame_count = \
        int(round(TEST_RECORDING_DURATION * TEST_RECORDING_SAMPLE_RATE))

    try:
        sd.rec(
            device=TEST_RECORDING_DEVICE_INDEX,
            channels=TEST_RECORDING_CHANNEL_COUNT,
            samplerate=TEST_RECORDING_SAMPLE_RATE,
            dtype=TEST_RECORDING_SAMPLE_DTYPE,
            frames=frame_count,
            blocking=True)
        
    except Exception as e:
        print('Test recording failed with message: {e}')
   

if __name__ == '__main__':
    main()
