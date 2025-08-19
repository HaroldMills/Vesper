"""Runs the Vesper Recorder."""


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

* Add Ctrl-C interrupts. Test on macOS, Windows, and Raspberry Pi OS.

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
    main_process = MainProcess()
    main_process.start()
    main_process.join()


if __name__ == '__main__':
    _main()
