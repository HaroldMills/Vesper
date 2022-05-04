"""
Functions that return external URLs, for example for the Vesper documentation.
"""


import vesper.version as vesper_version


_USE_LATEST_DOCUMENTATION_VERSION = False
"""Set this `True` during development, `False` for release."""


def _create_documentation_url():
    
    if _USE_LATEST_DOCUMENTATION_VERSION:
        doc_version = 'latest'
    else:
        doc_version = vesper_version.full_version
        
    return 'https://vesper.readthedocs.io/en/' + doc_version + '/'


def _create_tutorial_url():
    return _create_documentation_url() + 'tutorial.html'


documentation_url = _create_documentation_url()

tutorial_url = _create_tutorial_url()

source_code_url = 'https://github.com/HaroldMills/Vesper'
