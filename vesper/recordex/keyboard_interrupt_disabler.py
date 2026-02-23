"""
Module whose import disables keyboard interrupts in the current process.

Any Vesper Recorder module that defines a recorder process (i.e. the
`RecorderProcess` class and its subclasses) should import this module
first thing. This will disable keyboard interrupts in the process as
soon as possible during startup. The main Vesper Recorder process is
the only process that should receive keyboard interrupts, so that it
can direct the orderly shutdown of all the other processes.

The main Vesper Recorder process imports this module first thing to
disable keyboard interrupts temporarily, and then re-enables them in its
`main` function. Having the recorder unresponsive to keyboard interrupts
during the main module's import phase is not ideal, but I don't think it's
a big problem since that phase is usually pretty quick.

To avoid having the recorder unresponsive to keyboard interrupts during
the main module's import phase, I tried disabling keyboard interrupts only
in non-main processes by checking to see if `mp.parent_process()` is `None`,
but that didn't work, since `mp.parent_process()` is always `None` during
the module import phase of a process, regardless of whether or not the
process is the main process. There are other ways we could try to determine
whether we're in the main process, such as by checking to see if process
name `mp.current_process().name` is `"MainProcess"`, but that and all of
the other ones I'm aware of seem brittle, so I think it's better not to
use them.
"""


# import multiprocessing as mp
# print(
#     f'Disabling keyboard interrupts in process '
#     f'"{mp.current_process().name}".')

import signal
signal.signal(signal.SIGINT, signal.SIG_IGN)
