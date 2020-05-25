"""
Setup.py for Vesper pip package.

All of the commands below should be issued from the directory containing
this file.

To build the Vesper package:

    python setup.py sdist bdist_wheel
    
To upload the Vesper package to the test Python package index:

    python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    
To upload the Vesper package to the  real Python package index:

    python -m twine upload dist/*
    
To create a conda environment using a local Vesper package:

    conda create -n test python=3.6
    conda activate test
    pip install dist/vesper-<version>.tar.gz
    
To create a conda environment using a Vesper package from the test PyPI:

    conda create -n test python=3.6
    conda activate test
    pip install birdvoxdetect django jsonschema pyephem resampy ruamel_yaml scipy
    pip install --extra-index-url https://test.pypi.org/simple/ vesper==<version>
    
The first pip command in the above is to ensure that Vesper's dependencies
are installed from the real PyPI rather than the test one, which can
contain incompatible pre-release versions.
    
To create a conda environment using a Vesper package from the real PyPI:

    conda create -n test python=3.6
    conda activate test
    pip install vesper==<version>
    
To create a conda environment for Vesper development with Tensorflow 1.x:

    conda create -n vesper-dev python=3.6
    conda activate vesper-dev
    pip install birdvoxdetect bokeh django jsonschema matplotlib pyephem ruamel_yaml sphinx sphinx_rtd_theme
    
To create a conda environment for Vesper development with TensorFlow 2.x:
    conda create -n vesper-dev-tf2 python=3.7
    conda activate vesper-dev-tf2
    pip install bokeh django jsonschema matplotlib pyephem resampy ruamel_yaml sphinx sphinx_rtd_theme tensorflow
    
Whenever you modify plugin entry points, you must run:

    python setup.py develop
    
for the plugin manager to be able to see the changes. If you don't do this,
you will see ImportError exceptions when the plugin manager tries to load
entry points that no longer exist.
"""


from pathlib import Path
from setuptools import find_packages, setup
import importlib
import sys


# Load `vesper.version` module as `version_module`. This code is modeled
# after the "Importing a source file directly" section of
# https://docs.python.org/3/library/importlib.html#module-importlib.
module_name = 'vesper.version'
module_path = Path('vesper/version.py')
spec = importlib.util.spec_from_file_location(module_name, module_path)
version_module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = version_module
spec.loader.exec_module(version_module)


setup(
      
    name='vesper',
    version=version_module.full_version,
    description=(
        'Software for acoustical monitoring of nocturnal bird migration.'),
    url='https://github.com/HaroldMills/Vesper',
    author='Harold Mills',
    author_email='harold.mills@gmail.com',
    license='MIT',
    
    # We exclude the unit test packages since some of them contain a
    # lot of data, for example large audio files.
    packages=find_packages(
        exclude=['tests', 'tests.*', '*.tests.*', '*.tests']),
    
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    
    install_requires=[
        'birdvoxdetect',
        'django',
        'jsonschema',
        'pyephem',
        'resampy',
        'ruamel_yaml',
        'scipy'
    ],
      
    entry_points={
        'console_scripts': [
            'vesper_admin=vesper.django.manage:main',
            'vesper_recorder=vesper.scripts.vesper_recorder:_main',
            'vesper_play_recorder_test_signal=vesper.scripts.play_recorder_test_signal:_main',
            'vesper_show_audio_input_devices=vesper.scripts.show_audio_input_devices:_main'
        ]
    },
      
    include_package_data=True,
    zip_safe=False
    
)
