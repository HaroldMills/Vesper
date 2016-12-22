"""Shows PyAudio host API and device information."""


import pyaudio


def _main():
    
    p = pyaudio.PyAudio()
    
    _show_host_apis(p)
    print()
    
    _show_devices(p)
    print()
    
    _show_default_input_device_info(p)
    print()

    p.terminate()
    
    
def _show_host_apis(p):
    
    host_api_count = p.get_host_api_count()
    
    if host_api_count == 0:
        print('no PortAudio host APIs found')
        
    else:
        print('PortAudio host APIs:')
        for i in range(host_api_count):
            info = p.get_host_api_info_by_index(i)
            print('{} "{}"'.format(i, info['name']))
    

def _show_devices(p):
    
    device_count = p.get_device_count()
    
    if device_count == 0:
        print('no PortAudio devices found')
        
    else:
        print('PortAudio devices:')
        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            _show_device_info(i, info)
            
            
def _show_device_info(index, info):
    print('{} {} "{}" {} {} {} {} {}'.format(
        index, info['hostApi'], info['name'], info['maxInputChannels'],
        info['maxOutputChannels'], info['defaultSampleRate'],
        info['defaultLowInputLatency'], info['defaultHighInputLatency']))
            
            
def _show_default_input_device_info(p):
    
    try:
        info = p.get_default_input_device_info()
        
    except IOError:
        print('No default input device available.')
        
    else:
        print('Default input device:')
        _show_device_info(None, info)
    
    
if __name__ == '__main__':
    _main()
    