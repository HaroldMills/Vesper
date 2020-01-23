from pathlib import Path
from setuptools import find_packages, setup
import importlib
import sys


# Load `vesper.version` module as `version_module`. This code is modeled
# after the "Importing a source file directly" section of
# https://docs.python.org/3/library/importlib.html#module-importlib.
module_name = 'vesper.version'
module_path = Path('../vesper/version.py')
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
        'django',
        'h5py==2.9.0',
        'jsonschema',
        # 'keras==2.2.4',
        'librosa==0.7.0',
        'numpy==1.16.4',
        'pandas==0.25.1',
        'pyephem',
        'resampy',
        'ruamel_yaml',
        'scikit-learn==0.21.2',
        'scipy'
        # 'tensorflow~=1.12.2'
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
