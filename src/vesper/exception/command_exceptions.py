"""
Module containing classes of exceptions pertaining to Vesper commands.
"""


class CommandError(Exception):
    pass


class CommandFormatError(CommandError):
    pass


class CommandExecutionError(CommandError):
    pass
