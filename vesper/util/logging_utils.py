"""Utilities pertaining to logging."""


from logging import Formatter
import logging
import traceback


# TODO: Include logging Python module names in log messages, and make
# log messages easier to parse into parts. The following is a possibility.
# We put the time of a log message first for sorting purposes. We put the
# message text last so a log line can be split into its parts relatively
# easily, even if the text happens to contain one or more separators. We
# put the level name just before the message since that reads nicely.
# Note that to get Python module names into log messages, we will have
# to modify not only this module but all of the places where other
# modules get their loggers. They currently get the root logger instead
# of a module-specific one.
# _MESSAGE_FORMAT = '|'.join((
#     '%(asctime)s.%(msecs)03d', '%(name)s', '%(levelname)s', '%(message)s'))

_MESSAGE_FORMAT = '%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s'
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def configure_root_logger():
    logging.basicConfig(format=_MESSAGE_FORMAT, datefmt=_DATE_FORMAT)


def create_formatter():
    return Formatter(fmt=_MESSAGE_FORMAT, datefmt=_DATE_FORMAT)


def append_stack_trace(message):
    return message + ' See stack trace below.\n' + traceback.format_exc()
