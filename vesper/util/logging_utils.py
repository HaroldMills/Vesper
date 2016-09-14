"""Utilities pertaining to logging."""


import traceback


def append_stack_trace(message):
    return message + ' See stack trace below.\n' + traceback.format_exc()
