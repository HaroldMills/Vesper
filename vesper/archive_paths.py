"""
Module containing archive directory and file paths.

The `archive_paths` attribute of this module is a `Bunch` whose
attributes are the absolute paths of various archive directories.

A Vesper Django app sets the paths that it defines in `archive_paths`
on startup, in its `AppConfig.ready` method. The paths are typically
derived from paths defined in the project settings.
"""


from vesper.util.bunch import Bunch


archive_paths = Bunch()
