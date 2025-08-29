"""Runs the Vesper Recorder."""


import signal


# The Vesper Recorder comprises several processes. We refer to the one
# that executes the `main` function of this module as the *bootstrap
# process*. The bootstrap process starts before all the other recorder
# processes and is responsible for starting the *main process*, which
# in turn starts the other recorder processes.
#
# We want to handle keyboard interrupts (initiated when the user types
# Ctrl-C on the keyboard) in the bootstrap process and ignore them in
# all other processes. The following code turns off keyboard interrupts
# for all processes. It runs in every recorder processe, including the
# bootstrap process, the main process, and every other process, to
# disable keyboard interrupts as soon as possible as the process is
# starting up. The `main` function of this module then turns keyboard
# interrupts back on for only the bootstrap process.
#
# The code here runs in every recorder process since we are using the
# `spawn` multiprocessing start method, under which Python executes
# this module (the so-called *entry module*) first in every program
# process.
try:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
except Exception as e:
    import sys
    print(
        f'Attempt to ignore keyboard interrupts at recorder process '
        f'startup raised an exception that will be ignored. As a result, '
        f'keyboard interrupts may not work properly. '
        f'Exception message was: {e}', file=sys.stderr)


import multiprocessing as mp
import threading


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
    signal.signal(signal.SIGINT, handle_keyboard_interrupt)

    # We do this after setting up keyboard interrupt handling instead
    # of in the usual place near the top of this file so that the
    # keyboard interrupt setup can happen as soon as possible. This
    # reduces the initial period during which the recorder is
    # unresponsive to keyboard interrupts.
    from vesper.recordex.main_process import MainProcess

    # Create and start main recorder process.
    main_process = MainProcess()
    main_process.start()

    try:
        
        while main_process.is_alive():
            
            # Check for keyboard interrupt periodically.
            if keyboard_interrupt_event.is_set():
                break
            
            main_process.join(timeout=1)
    
    except KeyboardInterrupt:
        # keyboard interrupt delivered as `KeyboardInterrupt` exception
        # instead of via call to `handle_keyboard_interrupt`

        # Set keyboard interrupt event, even if nobody will use it, to
        # maintain the invariant that it is set if and only if we have
        # received a keyboard interrupt.
        keyboard_interrupt_event.set()
    
    finally:
        
        # Stop and join main process. Sometimes it will already have
        # stopped, but that's okay.
        try:
            main_process.stop()
        finally:
            main_process.join()


if __name__ == '__main__':
    main()
