#!/bin/bash

# Linux shell script that starts the Vesper Recorder.
#
# See instructions in Vesper Recorder `README.md` for how to install this
# on a Raspberry Pi so that the recorder starts whenever the Raspberry
# Pi does.

# Activate the `vesper-recorder` Conda environment.
source /home/harold/miniforge3/bin/activate
source activate vesper-recorder

# Start the Vesper Recorder from its home directory.
cd /home/harold/Desktop/Vesper\ Recorder
vesper_recorder
