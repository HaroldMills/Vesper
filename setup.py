from setuptools import find_packages, setup


setup(
      
    name='vesper',
    version='0.1.0',
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
        'matplotlib',
        'pandas',
        'pyephem',
        'pyyaml',
        'scikit-learn'
    ],
      
    entry_points={
        'console_scripts': ['vcl=vesper.vcl.vcl:main'],
        'gui_scripts': ['vesper_viewer=vesper.ui.vesper_viewer:main']
    },
      
    include_package_data=True,
    zip_safe=False
    
)
