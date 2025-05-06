"""
Script that lists all available PortAudio audio input devices and their
host API names.
"""


import sounddevice as sd


def main():

    devices = get_input_devices()

    if len(devices) == 0:
        print('No audio input devices found.')

    else:
        print('Audio input devices (device name, host API name):\n')
        lines = [
            f'    ({device_name}, {host_api_name})\n'
            for device_name, host_api_name in devices]
        device_table = ''.join(lines)
        print(device_table)


def get_input_devices():
    
    # Get input device info.
    all_devices = sd.query_devices()
    input_devices = [d for d in all_devices if d['max_input_channels'] > 0]
    
    # Get host API info.
    host_apis = sd.query_hostapis()

    # Get input device (device_name, host_api_name) pairs.
    input_devices = \
        [get_input_device_info(d, host_apis) for d in input_devices]
    
    # Sort input devices by name and host API name.
    input_devices.sort()

    return input_devices
    
    
def get_input_device_info(device, host_apis):

    device_name = device['name']

    host_api_index = device['hostapi']
    host_api = host_apis[host_api_index]
    host_api_name = host_api['name']

    return device_name, host_api_name


if __name__ == '__main__':
    main()
