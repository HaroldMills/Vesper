"""Runs the Vesper Recorder."""


import signal


# The Vesper Recorder comprises several processes. We refer to the one
# that executes the `_main` function of this module as the *bootstrap
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
# starting up. The `_main` function of this module then turns keyboard
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


'''
Tasks:

+ Move process classes to their own modules.

+ Make `_main` a minimal function that just creates, starts, and joins
  the main process. Call the process that runs `_main` the *bootstrap
  process*. Do not do any logging in the bootstrap process.

+ Add `_set_up_logging` and `_tear_down_logging` methods to `RecorderProcess`.
  Call the methods from the `run` method. The default implementations of
  the methods raise `NotImplementedError`.

+ Implement `_set_up_logging` and `_tear_down_logging` for `MainProcess`.

+ Create a `RecorderSubprocess` class that inherits from `RecorderProcess`.
  Implement `_set_up_logging` and `_tear_down_logging` for subprocesses in it.

+ Modify `AudioInputProcess` to inherit from `RecorderSubprocess`.

+ Add Ctrl-C interrupts. Test on macOS, Windows, and Raspberry Pi OS.

* Decide on "Error message was:" vs. "Exception message was:".

* Be thinking about InterruptException exception handling on Windows.
  Would having a process state and handling such exceptions based on that
  state help? I think that at some point you have to stop trying to
  respond gracefully for every conceivable point of interruption. Maybe,
  for example, we just don't worry about interruptions during startup,
  when some stuff has been initialized and some not. Maybe we just keep
  track of whether or not initialization is complete and respond to
  interrupts accordingly.

* Add some very simple YAML settings. Parse them so that if parsing fails
  you see a nice error message indicating where the problem is. Test on
  macOS, Windows, and Raspberry Pi OS.

* Add settings parsing for real.

* Add audio input.

* Add audio processor process.

* Add schedule thread.

* Add S3 file uploader sidecar.

* Add WAVE to FLAC converter sidecar.

* Add UI thread.

* Add start/stop button to UI.

* Add dynamic level meter to UI.
'''


def _main():

    # Use the `spawn` multiprocessing start method on all platforms.
    # As of Python 3.12, this is the default for Windows and macOS
    # but not for POSIX. On POSIX the default start method is `fork`,
    # which is fast but copies more parent process state to the child
    # process than we need or want. The extra state can cause problems.
    # For example, in an earlier version of the recorder's multiprocess
    # logging system it caused some log messages to be duplicated on
    # POSIX.
    mp.set_start_method('spawn')

    # Create event that we'll set if we receive a keyboard interrupt.
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

        # We don't need to set `keyboard_interrupt_event` here since we've
        # already exited the above loop.
        pass
    
    finally:
        
        # Stop and join main process. Sometimes it will already have
        # stopped, but that's okay.
        try:
            main_process.stop()
        finally:
            main_process.join()


if __name__ == '__main__':
    _main()
