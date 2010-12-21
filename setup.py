"""
PySonde
-------

PySonde is a module for reading water quality data from various sensor
formats.

"""
from setuptools import Command, setup

def run_tests():
    import os, sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'tests'))
    from tests import suite
    return suite()

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
    packages=['sonde'],
    platforms='any',
    install_requires=[
        'pytz>=2010o',
        'seawater>=1.0.5',
        'numpy>=1.5.0',
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
    ],
    test_suite='__main__.run_tests',
)
