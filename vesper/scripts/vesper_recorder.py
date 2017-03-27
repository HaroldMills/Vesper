"""Records audio to .wav files according to a schedule."""


import argparse
import sys
import time

from vesper.util.vesper_recorder import VesperRecorder


def _main():
    
    config_file_path = _parse_args()
    
    # TODO: Configure logging, and use it instead of the `print` function
    # in this script and in the `vesper_recorder` module.
    
    try:
        config = VesperRecorder.parse_config_file(config_file_path)
    except Exception as e:
        print(
            'Could not parse configuration file. Error message was: {}'.format(
                str(e)), file=sys.stderr)
        sys.exit(1)
    
    recorder = VesperRecorder(config)
    
    print('Starting recorder...')
    recorder.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Recorder interrupted via keyboard.')
         
 
def _parse_args():
    parser = argparse.ArgumentParser(
        description='Records audio according to a schedule.')
    parser.add_argument('config_file_path', help='configuration file path')
    args = parser.parse_args()
    return args.config_file_path


if __name__ == '__main__':
    _main()
