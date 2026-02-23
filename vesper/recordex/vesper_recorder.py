"""
The main module of the Vesper Recorder.

This module runs in the Vesper Recorder's main process, and starts the
*recorder process*, which in turn starts all of the other recorder
processes, including the audio input, audio processing, and sidecar
processes. The main process is also responsible for handling keyboard
interrupts and directing the orderly shutdown of all of the other
recorder processes.
"""


# Disable keyboard interrupts. The `main` function below will re-enable them
# for the main process.
#
# Note that it is not sufficient to disable keyboard interrupts here and
# not at the tops of the other recorder process modules. That would work
# on macOS since there this module is imported first thing in all
# recorder processes, but on Windows 10, at least, it is not.
import vesper.recordex.keyboard_interrupt_disabler

import multiprocessing as mp
import signal
import threading

# Note that this import will also disable keyboard interrupts in the main
# process, in addition to the above `keyboard_interrupt_disabler` import.
# We choose not to rely on that, however, and to make the disablement
# explicit.
from vesper.recordex.recorder_process import RecorderProcess


def main():

    # Use the `spawn` multiprocessing start method on all platforms.
    # As of Python 3.12, this is the default for Windows and macOS
    # but not for POSIX. On POSIX the default start method is `fork`,
    # which is fast but copies more parent process state to the child
    # process than we need or want. The extra state can cause problems.
    # For example, in an earlier version of the recorder's multiprocess
    # logging system it caused some log messages to be duplicated on
    # POSIX.
    mp.set_start_method('spawn')

    # Create event that is set if and only if we have received a keyboard
    # interrupt.
    keyboard_interrupt_event = threading.Event()

    # Register keyboard interrupt handler.
    def handle_keyboard_interrupt(signal_num, frame):
        keyboard_interrupt_event.set()
    # print(
    #     f'Registering keyboard interrupt handler in process '
    #     f'"{mp.current_process().name}".')
    signal.signal(signal.SIGINT, handle_keyboard_interrupt)

    # Create and start recorder process.
    recorder_process = RecorderProcess()
    recorder_process.start()

    try:
        
        while recorder_process.is_alive():
            
            # Check for keyboard interrupt periodically.
            if keyboard_interrupt_event.is_set():
                break
            
            recorder_process.join(timeout=1)
    
    except KeyboardInterrupt:
        # keyboard interrupt delivered as `KeyboardInterrupt` exception
        # instead of via call to `handle_keyboard_interrupt`

        # Set keyboard interrupt event, even if nobody will use it, to
        # maintain the invariant that it is set if and only if we have
        # received a keyboard interrupt.
        keyboard_interrupt_event.set()
    
    finally:
        
        if recorder_process.is_alive():
            # recorder process is still running

            try:

                # Tell recorder process to stop.
                recorder_process.stop_event.set()

            finally:

                # Wait for recorder process to stop.
                recorder_process.join()


if __name__ == '__main__':
    main()
