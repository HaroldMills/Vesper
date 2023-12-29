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
    pip install soxr
    pip install -e .
    
To run the Vesper Recorder, run the following commands in an Anaconda
Prompt or terminal window:

    conda activate vesper-recorder-dev
    vesper_recorder
"""


from pathlib import Path

from vesper.recorder.vesper_recorder import VesperRecorder


def _main():
    home_dir_path = Path.cwd()
    VesperRecorder.create_and_run_recorder(home_dir_path)
        

if __name__ == '__main__':
    _main()
