"""
PySonde
-------

PySonde is a module for reading water quality data from various sensor
formats.

"""
from setuptools import Command, setup, find_packages

# note: the minimum version numbers are just what I know will work,
# but they could probably be a few versions lower
setup(
    name='PySonde',
    version='0.1',
    license='BSD',
    author='Dharhas Pothina',
    author_email='dharhas.pothina@twdb.state.tx.us',
    maintainer='Andy Wilson',
    maintainer_email='andrew.wilson@twdb.state.tx.us',
    description='A utility library for reading various water quality '
                'data formats',
    long_description=__doc__,
    keywords='sonde water quality format environment ysi',
    packages=find_packages(),
    package_data={'': ['data/ysi_param.def']},
    platforms='any',
    install_requires=[
        'numpy>=1.5.0',
        'pytz>=2010o',
        'quantities>=0.9.0',
        'seawater>=1.0.5',
        'xlrd>=0.7.1',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    tests_require=[
        'nose>=0.11.4',
        'configobj>=4.7.2',
    ],
    test_suite='nose.collector',
)
