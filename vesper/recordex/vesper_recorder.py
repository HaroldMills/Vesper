"""Runs the Vesper Recorder."""


import signal
import threading

from vesper.recordex.main_process import MainProcess


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

    # Create event that we'll set if we receive a SIGINT (i.e. Ctrl-C) signal.
    sigint_event = threading.Event()

    # Register SIGINT handler.
    def handle_sigint(signal_num, frame):
        sigint_event.set()
    signal.signal(signal.SIGINT, handle_sigint)

    # Create and start main recorder process.
    main_process = MainProcess()
    main_process.start()

    try:
        
        while main_process.is_alive():
            
            # Check SIGINT event periodically.
            if sigint_event.is_set():
                break
            
            main_process.join(timeout=1)
    
    except KeyboardInterrupt:
        # SIGINT delivered as `KeyboardInterrupt` exception instead of
        # via call to `handle_sigint`

        # We don't need to set `sigint_event` here since we're already
        # out of the above loop.
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
