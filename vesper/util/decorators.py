"""Module containing Python decorators for use in Vesper."""


def synchronized(method):

    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper
