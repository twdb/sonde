.. _api:

API
===

.. module:: sonde


The easiest way to read a data file is through its format interface::

    from sonde import Sonde
    dataset = Sonde('path/to/ysi_file.dat', 'ysi', param_def='path/to/ysi_param.def')

    dataset.dates   # contains a numpy array of datetime objects
    dataset.data    # contains a dict with numpy arrays for each data field mapped to the field name





Sonde Object
------------

.. autoclass:: sonde.formats.ysi.Dataset
   :members:
   :inherited-members:


.. autoclass:: Sonde
   :members:
   :inherited-members:
   
