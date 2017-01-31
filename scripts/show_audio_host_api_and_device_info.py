"""Shows PyAudio host API and device information."""


import pyaudio


def _main():
    
    pa = pyaudio.PyAudio()
    
    _show_host_apis(pa)
    print()
    
    _show_input_devices(pa)
    print()
    
    _show_default_input_device_info(pa)
    print()
    
    _show_output_devices(pa)
    print()
    
    _show_default_output_device_info(pa)
    print()
    
    pa.terminate()
    
    
def _show_host_apis(pa):
    
    host_api_count = pa.get_host_api_count()
    
    if host_api_count == 0:
        print('no PortAudio host APIs found')
        
    else:
        print('PortAudio host APIs:')
        for i in range(host_api_count):
            info = pa.get_host_api_info_by_index(i)
            print('{} "{}"'.format(i, info['name']))
    

def _show_input_devices(pa):
    _show_devices(pa, 'input', 'maxInputChannels')
    
    
def _show_devices(pa, type_name, num_channels_key):
    
    infos = [i for i in _get_device_infos(pa) if i[num_channels_key] != 0]
    
    if len(infos) == 0:
        print('No {} devices found.'.format(type_name))
        
    else:
        print('{} devices:'.format(type_name.capitalize()))
        for info in infos:
            _show_device_info(info)
            
    
def _get_device_infos(pa):
    num_devices = pa.get_device_count()
    return [pa.get_device_info_by_index(i) for i in range(num_devices)]
            
            
def _show_device_info(info):
    print('{} {} "{}" {} {} {} {} {}'.format(
        info['hostApi'], info['index'], info['name'], info['maxInputChannels'],
        info['maxOutputChannels'], info['defaultSampleRate'],
        info['defaultLowInputLatency'], info['defaultHighInputLatency']))
            
            
def _show_default_input_device_info(pa):
    
    try:
        info = pa.get_default_input_device_info()
        
    except IOError:
        print('No default input device available.')
        
    else:
        print('Default input device:')
        _show_device_info(info)
    
    
def _show_output_devices(pa):
    _show_devices(pa, 'output', 'maxOutputChannels')
    
    
def _show_default_output_device_info(pa):
    
    try:
        info = pa.get_default_output_device_info()
        
    except IOError:
        print('No default output device available.')
        
    else:
        print('Default output device:')
        _show_device_info(info)
    
    
if __name__ == '__main__':
    _main()
    