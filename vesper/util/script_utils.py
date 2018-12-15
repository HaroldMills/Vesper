"""Script utility functions."""


import os


def announce(text):
    command = 'say "{}"'.format(text)
    os.system(command)
