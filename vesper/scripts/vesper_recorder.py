"""
Script version of the Vesper Recorder.

The script takes no arguments.

The Vesper Recorder uses a *home directory* whose location is the
current working directory, i.e. the directory in which the recorder
was started. The home directory must contain a YAML configuration file
named `Vesper Recorder Config.yaml`. An example configuration file
including extensive comments is distributed with the recorder.

The recorder logs messages to the file `Vesper Recorder Log.txt`, also in
the recorder home directory. This script also logs essentially the same
messages to the console.

To create a Conda environment in which to develop the Vesper Recorder,
issue the following commands from your Vesper Git repo folder:

    conda create -n vesper-recorder-dev python=3.11
    conda activate vesper-recorder-dev
    conda install -c conda-forge python-sounddevice
    pip install -e .
    
To run the Vesper Recorder, run the following commands in an Anaconda
Prompt or terminal window:

    conda activate vesper-recorder-dev
    vesper_recorder
"""


from pathlib import Path
import multiprocessing

from vesper.recorder.vesper_recorder import VesperRecorder


def _main():

    # Use the `spawn` multiprocessing start method on all platforms.
    # As of Python 3.12, this is the default for Windows and macOS
    # but not for POSIX. On POSIX the default start method is `fork`,
    # which is fast but copies more parent process state to the child
    # process than we need or want. The extra state can cause problems.
    # For example, in an earlier version of the recorder's multiprocess
    # logging system it caused some log messages to be duplicated on
    # POSIX.
    #
    # Note that according to the Python 3.12.4 documentation for the
    # `multiprocessing` module (see https://docs.python.org/3/library/
    # multiprocessing.html#contexts-and-start-methods), the default
    # start method for POSIX will change away from `fork` for Python
    # 3.14. If after that change it is `spawn` (or something else we
    # can work with) for all platforms, we might no longer need to
    # set it explicitly.
    multiprocessing.set_start_method('spawn')
    
    home_dir_path = Path.cwd()
    
    VesperRecorder.create_and_run_recorder(home_dir_path)
        

if __name__ == '__main__':
    _main()
