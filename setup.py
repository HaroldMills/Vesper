from setuptools import find_packages, setup


setup(
      
    name='vesper',
    version='0.3.2',
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
    
    install_requires=[
        'django>=1.11',
        'django<1.12',
        'jsonschema',
        'numpy',
        'pyephem',
        'pytz',
        'pyyaml',
        'scikit-learn'
    ],
      
    entry_points={
        'console_scripts': [
            'vesper_admin=vesper.django.manage:main',
            'vesper_recorder=vesper.scripts.vesper_recorder',
            'vesper_play_recorder_test_signal=vesper.scripts.play_recorder_test_signal',
            'vesper_show_audio_input_devices=vesper.scripts.show_audio_input_devices'
        ]
    },
      
    include_package_data=True,
    zip_safe=False
    
)
