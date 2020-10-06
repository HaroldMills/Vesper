"""
Script version of the Vesper Recorder.

The script takes no arguments.

The Vesper Recorder requires a home directory whose location is specified
by the `VESPER_RECORDER_HOME` environment variable. The home directory
must contain a YAML configuration file named `Vesper Recorder Config.yaml`.
An example configuration file including extensive comments is distributed
with the recorder.

The recorder logs messages to the file `Vesper Recorder Log.txt`, also in
the recorder home directory. This script also logs essentially the same
messages to the console.

To create a conda environment in which to run the Vesper Recorder:

    conda create -n vesper_recorder python
    conda activate vesper_recorder
    conda install pyaudio
    pip install jsonschema pyephem pytz ruamel.yaml
    
To run the Vesper Recorder, you must have the PYTHONPATH and
VESPER_RECORDER_HOME environment variables set. On Unix, for example:

    export PYTHONPATH="/Users/Harold/Documents/Code/Python/Vesper/vesper"
    export VESPER_RECORDER_HOME="/Users/Harold/Desktop/Vesper Recorder"
    
Then, in an Anaconda Prompt or terminal window, run the Vesper Recorder
script:

    conda activate vesper_recorder
    python -m vesper.scripts.vesper_recorder
"""


from logging import Formatter, StreamHandler
import logging
import time

from vesper.util.vesper_recorder import VesperRecorder


_logger = logging.getLogger(__name__)


def _main():
    
    _initialize_logging()
    
    recorder = VesperRecorder.create_and_start_recorder(
        'Welcome to the Vesper Recorder!')
    
    if recorder is not None:
        # recorder creation and start succeeded
        
        _wait_for_keyboard_interrupt() 
        
        _logger.info('Stopping recorder and exiting due to keyboard interrupt.')
        recorder.stop()
        recorder.wait()
         

def _initialize_logging():
    
    formatter = Formatter('%(asctime)s %(levelname)s %(message)s')
    
    # Create handler that writes log messages to stderr.
    stderr_handler = StreamHandler()
    stderr_handler.setFormatter(formatter)
    
    # Add handlers to root logger.
    logger = logging.getLogger()
    logger.addHandler(stderr_handler)
    
    # Set root logger level.
    logger.setLevel(logging.INFO)


def _wait_for_keyboard_interrupt():
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    _main()
