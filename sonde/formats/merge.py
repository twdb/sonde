"""
    sonde.formats.solinst
    ~~~~~~~~~~~~~~~~~

    This module implements the Solinst format.
    The files are in .lev format

"""
from __future__ import absolute_import

import datetime
import pkg_resources
import re
from StringIO import StringIO
import xlrd
import csv

import numpy as np
import quantities as pq

from .. import sonde
from .. import quantities as sq
from ..timezones import cdt, cst

class MergeDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data merged from multiple data files
    using sonde.merge
    timezone is default.timezone. parameter names/units are from the master list
    data is a dict containing all the data with param names and units.
    """
    def __init__(self, metadata, paramdata):
        self.manufacturer = metadata['instrument_manufacturer']
        self.data_file = metadata['data_file_name']
        self.default_tzinfo = sonde.default_timezone

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for param in paramdata.keys():
            self.parameters[param] = param
            self.data[param] = paramdata[param]

        self.format_parameters = {
            'serial_number' : metadata['instrument_serial_number']
            }

        self.dates = metadata['dates']
        #I don't think the following line is needed
        #super(MergeDataset, self).__init__()
