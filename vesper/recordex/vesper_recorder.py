"""Runs the Vesper Recorder."""


# import multiprocessing as mp
# print(f'Executing {__file__} in process "{mp.current_process().name}".')


import multiprocessing as mp
import signal
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

    # We perform this import after setting up keyboard interrupt
    # handling instead of in the usual place near the top of this file
    # so that the keyboard interrupt setup can happen as soon as
    # possible. This reduces the initial period during which the
    # recorder is unresponsive to keyboard interrupts.
    from vesper.recordex.recorder_process import RecorderProcess

    # Create and start main recorder process.
    main_process = RecorderProcess()
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
        
        if main_process.is_alive():
            # main process is still running

            try:

                # Tell main process to stop.
                main_process.stop_event.set()

            finally:

                # Wait for main process to stop.
                main_process.join()


if __name__ == '__main__':
    main()
