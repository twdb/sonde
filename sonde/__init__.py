"""
    PySonde
    ~~~~~~~

    A utility for reading in water data from a variety of device
    formats

"""

from .sonde import autodetect, BaseSondeDataset, default_static_timezone, \
     find_tz, master_parameter_list, merge, open_sonde, Sonde
from . import quantities
from . import formats
