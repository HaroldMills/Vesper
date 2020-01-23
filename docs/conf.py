# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
from pathlib import Path
import importlib
import sys

import sphinx_rtd_theme


# -- Project information -----------------------------------------------------

project = 'Vesper'
author = 'Harold Mills'
copyright = '2020, Harold Mills'

# Load `vesper.version` module as `version_module`. This code is modeled
# after the "Importing a source file directly" section of
# https://docs.python.org/3/library/importlib.html#module-importlib.
module_name = 'vesper.version'
module_path = Path('../vesper/version.py')
spec = importlib.util.spec_from_file_location(module_name, module_path)
version_module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = version_module
spec.loader.exec_module(version_module)

# Major project version, used as the replacement for |version|.
# This can be (but does not have to be) shorter than `release`,
# e.g. "1.2" instead of "1.2.3" or "1.2.3rc1".
version = version_module.full_version

# Full project version, used as the replacement for |release|.
release = version_module.full_version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

highlight_language = 'none'

master_doc = 'index'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_theme_options = {
    'style_nav_header_background': 'orange',
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
