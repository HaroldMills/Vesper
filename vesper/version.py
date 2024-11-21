"""
Module containing Vesper version.

This module is the authority regarding the Vesper version. Any other
module that needs the Vesper version should obtain it from this module.
"""


import re


# The authority for the Vesper version is the string-valued `__version__`
# attribute of this module. The Hatchling build backend that builds the
# `vesper` Python package is configured to read this attribute in the
# `tool.hatch.version` table of Vesper's `pyproject.toml` file. This
# module also parses the `__version__` attribute below to obtain its
# parts and construct version strings of various levels of detail. The
# version parts and strings are exposed as public module attributes.
__version__ = '0.4.15a0'

# Parse version number with regular expression.
_match = re.match(
    r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<suffix>.*)?$',
    __version__)

# Check that version number parsed.
if _match is None:
    raise ValueError(f'Invalid version string "{__version__}".')

# Get parts of version number.
major_number = int(_match.group('major'))
minor_number = int(_match.group('minor'))
patch_number = int(_match.group('patch'))
suffix = _match.group('suffix')

# Get various version numbers.
major_version = f'{major_number}'
minor_version = f'{major_version}.{minor_number}'
patch_version = f'{minor_version}.{patch_number}'
full_version = f'{patch_version}{suffix}'
