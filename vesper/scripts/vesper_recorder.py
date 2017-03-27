"""Records audio to .wav files according to a schedule."""


from logging import FileHandler, Formatter, StreamHandler
import argparse
import logging
import sys
import time

from vesper.util.vesper_recorder import VesperRecorder


_LOG_FILE_NAME = 'vesper_recorder.log'

_logger = logging.getLogger(__name__)


def _main():
    
    config_file_path = _parse_args()
    
    try:
        config = VesperRecorder.parse_config_file(config_file_path)
    except Exception as e:
        print(
            'Could not parse configuration file. Error message was: {}'.format(
                str(e)), file=sys.stderr)
        sys.exit(1)
    
    _configure_logging()
    
    _logger.info('Welcome to the Vesper recorder.')

    recorder = VesperRecorder(config)
    recorder.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _logger.info('Exiting due to keyboard interrupt.')
         
 
def _parse_args():
    parser = argparse.ArgumentParser(
        description='Records audio according to a schedule.')
    parser.add_argument('config_file_path', help='configuration file path')
    args = parser.parse_args()
    return args.config_file_path


def _configure_logging():
    
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    
    # Create handler that appends log messages to log file.
    file_handler = FileHandler(_LOG_FILE_NAME)
    file_handler.setFormatter(formatter)
    
    # Create handler that writes log messages to stderr.
    stderr_handler = StreamHandler()
    stderr_handler.setFormatter(formatter)
    
    # Add handlers to root logger.
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.addHandler(stderr_handler)
    
    # Set root logger level.
    logger.setLevel(logging.INFO)


if __name__ == '__main__':
    _main()
