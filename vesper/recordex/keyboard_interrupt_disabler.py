"""
Module whose import disables keyboard interrupts in the current process.

See main module docstring for a discussion of Vesper Recorder keyboard
interrupt handling.
"""

# import multiprocessing as mp
# print(
#     f'Disabling keyboard interrupts in process '
#     f'"{mp.current_process().name}".')

import signal
signal.signal(signal.SIGINT, signal.SIG_IGN)
