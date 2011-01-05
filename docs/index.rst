.. PySonde documentation master file, created by
   sphinx-quickstart on Mon Dec 13 12:30:08 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PySonde's documentation!
===================================

.. toctree::
   :maxdepth: 2

.. module:: sonde


Installation
------------

From the pysonde directory, run::

    python setup.py install



Quick start
-----------

The easiest way to read a data file is by using the Sonde function,
which takes a file path, a file format and then a series of
format-specific arguments::

    from sonde import Sonde
    dataset = Sonde('path/to/ysi_file.dat', 'ysi', param_def='path/to/ysi_param.def')

    dataset.dates   # contains a numpy array of datetime objects
    dataset.data    # contains a dict with numpy arrays for each data field mapped to the field name


    
Sonde Object
------------

.. autofunction:: Sonde

.. autoclass:: BaseSondeDataset
   :members:


   
Formats
-------
   
.. autoclass:: sonde.formats.ysi.YSIDataset
   :members:


   
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

