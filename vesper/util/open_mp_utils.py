"""Functions pertaining to the OpenMP library."""


import os


def work_around_multiple_copies_issue():

    """
    Works around an issue concerning multiple copies of the OpenMP runtime.
    
    The problem seems to arise when I install TensorFlow using Conda.
    It does not arise when I install TensorFlow using pip. I have seen
    the problem on both macOS and Windows. I'm not sure where the multiple
    copies are coming from. See
    https://github.com/openai/spinningup/issues/16 for an example of
    another person encountering this issue.
    """
    
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
