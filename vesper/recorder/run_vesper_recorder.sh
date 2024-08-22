#!/bin/bash

# Linux (including Raspberry Pi OS) shell script that sets the ALSA audio
# capture volume and starts the Vesper Recorder. Note that you can run this
# script on startup by putting a command like:
#
#     runuser -u harold /home/harold/Vesper\ Recorder/run_vesper_recorder.sh > /home/harold/Vesper\ Recorder/run_vesper_recorder.log 2>&1 &
#
# in your /etc/rc.local file.

# Set ALSA mixer audio capture volume control value. Run the `amixer contents`
# command to see information about the available controls, including their
# numids.
amixer cset numid=1 45%

# Activate the `vesper-recorder` Conda environment.
source /home/harold/miniforge3/bin/activate
source activate vesper-recorder

# Start the Vesper Recorder from its home directory.
cd /home/harold/Vesper\ Recorder
vesper_recorder
