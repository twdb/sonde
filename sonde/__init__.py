"""
    PySonde
    ~~~~~~~

    A utility for reading in water data from a variety of device
    formats
    
"""

from .sonde import BaseSondeDataset, master_parameter_list, Sonde
from . import quantities
from . import formats
