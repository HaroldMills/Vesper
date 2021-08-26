"""
Setup.py for Vesper pip package.

All of the commands below should be issued from the directory containing
this file.

To build the Vesper package:

    python setup.py sdist bdist_wheel

To upload the Vesper package to the test Python package index:

    python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

To upload the Vesper package to the real Python package index:

    python -m twine upload dist/*

To create a conda environment using a local Vesper package:

    conda create -n test python=3.9
    conda activate test
    pip install dist/vesper-<version>.tar.gz
    
To create a conda environment using a Vesper package from the test PyPI:

    conda create -n test python=3.9
    conda activate test
    pip install --extra-index-url https://test.pypi.org/simple/ vesper

To create a conda environment using a Vesper package from the real PyPI:

    conda create -n test python=3.9
    conda activate test
    pip install vesper==<version>

To create a conda environment for Vesper development with TensorFlow 1.15.x:
    conda create -n vesper-dev-tf115 python=3.6
    conda activate vesper-dev-tf115
    pip install bokeh django jsonschema matplotlib resampy ruamel_yaml skyfield sphinx sphinx_rtd_theme tensorflow~=1.15.0

To create a conda environment for Vesper development with TensorFlow 2.x:
    conda create -n vesper-dev-tf2 python=3.9
    conda activate vesper-dev-tf2
    conda install pyaudio
    pip install bokeh django jsonschema matplotlib resampy ruamel_yaml skyfield sphinx sphinx_rtd_theme tensorflow

To create a conda environment using the latest, local Vesper source code
and TensorFlow 2.x:
    conda create -n vesper-latest-tf2 python=3.9
    conda activate vesper-latest-tf2
    conda install pyaudio
    pip install -e /Users/harold/Documents/Code/Python/Vesper

Whenever you modify plugin entry points, you must run:

    python setup.py develop
    
for the plugin manager to be able to see the changes. If you don't do this,
you will see ImportError exceptions when the plugin manager tries to load
entry points that no longer exist.
"""


from importlib.machinery import SourceFileLoader
from pathlib import Path
from setuptools import find_packages, setup


def load_version_module(package_name):
    module_name = f'{package_name}.version'
    file_path = Path(f'{package_name}/version.py')
    loader = SourceFileLoader(module_name, str(file_path))
    return loader.load_module()


version = load_version_module('vesper')


setup(
      
    name='vesper',
    version=version.full_version,
    description=(
        'Software for acoustical monitoring of nocturnal bird migration.'),
    url='https://github.com/HaroldMills/Vesper',
    author='Harold Mills',
    author_email='harold.mills@gmail.com',
    license='MIT',
    
    # TODO: Consider making the `vesper` Python package a native
    # namespace package, allowing it to be split across multiple,
    # separate distribution packages to allow optional ones (e.g.
    # ones containing optional plugins) to be omitted from an
    # installation. See
    # https://packaging.python.org/guides/packaging-namespace-packages/
    # for a discussion of namespace packages.
    #
    # Two important points from that discussion are that:
    #
    # 1. Every distribution package that is part of a `vesper`
    #    namespace package must omit `__init__.py` from its `vesper`
    #    package directory. Note that this will affect where the
    #    `__version__` package attribute is defined, pushing it down
    #    one level of the package hierarchy, into the `__init__.py`
    #    of each subpackage. See PEP 396 for more about `__version__`
    #    for namespace packages.
    #
    # 2. The `setup.py` file of every distribution package must use
    #    `setuptools.find_namespace_packages` rather than
    #    `setuptools.find_packages` to find its packages.
    packages=find_packages(
        
        # We exclude the unit test packages since some of them contain a
        # lot of data, for example large audio files.
        exclude=['tests', 'tests.*', '*.tests.*', '*.tests']
    
    ),
    
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    
    install_requires=[
        'django~=3.2.0',
        'jsonschema~=3.2',
        'resampy',
        'ruamel_yaml',
        'skyfield~=1.38',
        'tensorflow~=2.6',
    ],
      
    entry_points={
        'console_scripts': [
            'vesper_admin=vesper.django.manage:main',
            'vesper_recorder=vesper.scripts.vesper_recorder:_main',
            'vesper_play_recorder_test_signal=vesper.scripts.play_recorder_test_signal:_main',
            'vesper_show_audio_input_devices=vesper.scripts.show_audio_input_devices:_main',
        ]
    },
      
    include_package_data=True,
    zip_safe=False
    
)
