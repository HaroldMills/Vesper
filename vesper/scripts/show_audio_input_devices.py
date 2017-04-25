"""Shows a list of available audio input devices."""


from vesper.util.vesper_recorder import VesperRecorder


def _main():
    
    devices = VesperRecorder.get_input_devices()
     
    if len(devices) == 0:
        print('No input devices were found.')
         
    else:
         
        print('Input devices:')
         
        default_found = False
         
        for d in devices:
             
            if d.default:
                prefix = '   *'
                default_found = True
            else:
                prefix = '    '
                 
            print('{}{} "{}"'.format(prefix, d.index, d.name))
             
        if default_found:
            print('The default device is marked with an asterisk.')
        else:
            print('No default device was found.')
              
              
if __name__ == '__main__':
    _main()
    