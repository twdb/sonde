"""
    sonde.formats.merge
    ~~~~~~~~~~~~~~~~~

    This module implements the Merge format used by sonde.merge

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
    Dataset object that represents the data merged from multiple data
    files using sonde.merge timezone is default.timezone. parameter
    names/units are from the master list data is a dict containing all
    the data with param names and units.
    """
    def __init__(self, metadata, paramdata):
        idx = self._indices_duplicate_data(metadata['dates'], paramdata)
        sort_idx = np.argsort(metadata['dates'][idx])
        self.manufacturer = metadata['instrument_manufacturer'][idx][sort_idx]
        self.serial_number = metadata['instrument_serial_number'][idx][sort_idx]
        self.data_file = metadata['data_file_name'][idx][sort_idx]
        self.default_tzinfo = sonde.default_static_timezone

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for param in paramdata.keys():
            self.parameters[param] = param
            self.data[param] = paramdata[param][idx][sort_idx]

        self.dates = metadata['dates'][idx][sort_idx]
        # I don't think the following line is needed
        # super(MergeDataset, self).__init__()

    def _indices_duplicate_data(self, dates, data):
        """
        return data index required to remove duplicate data
        """
        #convert to single structured array
        dtypes = [datetime.datetime]
        names = ['datetime']
        for param in data.keys():
            dtypes.append('f8')
            names.append(param)

        tmp_data = np.zeros(dates.size, dtype=np.dtype({'names': names,
                                                        'formats': dtypes}))
        tmp_data['datetime'] = dates
        for param in data.keys():
            tmp_data[param] = data[param]

        u, idx = np.unique(tmp_data, return_index=True)
        return idx
