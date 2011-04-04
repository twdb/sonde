"""
    sonde.formats.generic
    ~~~~~~~~~~~~~~~~~

    This module implements a generic format.
    The files are in .csv format and must conform to the
    following guidelines
    comments and metadata at top of file in the format:
      # name: value
    a timezone field: (UTC-?, the data must all be in one UTC offset)
      # timezone: UTC-6
    a fill_value field:
      # fill_value = -999.99
    the last two comment/header lines should be the following
    parameter header prepended by single #:
      # datetime, air_pressure, water_specific_conductance, etc
      (datetime must be first field and in format yyyy/mm/dd HH:MM:SS)
      (parameter names must be from master_param_list
    unit header prepended by single #:
      yyyy/mm/dd HH:MM:SS, Pa, mS/cm, PSU, degC, mH2O, n/a, n/a, n/a
      (units must be from supported_units_list)

    comma seperated data

    special columns or header items:
        original_data_file_name, instrument_manufacturer,
          instrument_serial_number
        if these exist they will overide self.manufacturer,
        self.data_file and self.serial_number

"""
from __future__ import absolute_import

import csv
import datetime
import pkg_resources
import re
from StringIO import StringIO
import warnings
import xlrd

import numpy as np
import quantities as pq

from .. import sonde
from .. import quantities as sq
from ..timezones import UTCStaticOffset


class GenericDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a generic csv
    file.
    """
    def __init__(self, data_file):
        self.manufacturer = 'generic'
        self.file_format = 'generic'
        self.data_file = data_file
        super(GenericDataset, self).__init__(data_file)

    def _read_data(self):
        """
        Read the generic data file
        """

        unit_map = {'degc': pq.degC,
                    'degf': pq.degC,
                    'm': sq.mH2O,
                    'mh2o': sq.mH2O,
                    'ft': sq.ftH2O,
                    'fth2o': sq.ftH2O,
                    'ms/cm': sq.mScm,
                    'psu': sq.psu,
                    'pa': pq.Pa,
                    'v': pq.volt,
                    'mg/l': sq.mgl,
                    '%': pq.percent,
                    'nd': pq.dimensionless,
                    'ntu': sq.ntu,
                    }

        generic_data = GenericReader(self.data_file)
        self.parameters = dict()
        self.data = dict()
        metadata = dict()

        for parameter in generic_data.parameters:
            if parameter.unit != 'n/a':
                if parameter.name.lower() in sonde.master_parameter_list:
                    pcode = parameter.name.lower()
                else:
                    warnings.warn('Un-mapped Parameter: %s' %
                                  parameter.name.lower(),
                                  Warning)
                try:
                    punit = unit_map[(parameter.unit.lower()).strip()]
                    if not np.all(np.isnan(parameter.data)):
                        self.parameters[pcode] = sonde.master_parameter_list[pcode]
                        self.data[pcode] = parameter.data * punit
                except KeyError:
                    warnings.warn('Un-mapped Unit Type\n'
                                  'Unit Name: %s' % parameter.unit,
                                  Warning)
            else:
                metadata[parameter.name.lower()] = parameter.data

        self.format_parameters = generic_data.format_parameters

        #overide default metadata if present in file
        names = ['manufacturer', 'data_file', 'serial_number']
        kwds = ['instrument_manufacturer', 'original_data_file',
                'instrument_serial_number']
        for name, kwd in zip(names, kwds):
            #check format_parameters
            idx = [i for i
                   in self.format_parameters.keys() if i.lower() == kwd]
            if idx != []:
                exec('self.' + name + '=self.format_parameters[idx[0]]')
            idx = [i for i in metadata.keys() if i.lower() == kwd]
            if idx != []:
                exec('self.' + name + ' = metadata[idx[0]]')

        self.dates = generic_data.dates


class GenericReader:
    """
    A reader object that opens and reads a Solinst lev file.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """
    def __init__(self, data_file):
        self.num_params = 0
        self.parameters = []
        self.format_parameters = {}
        self.read_generic(data_file)
        self.dates = [i.replace(tzinfo=self.default_tzinfo)
                      for i in self.dates]

    def read_generic(self, data_file):
        """
        Open and read a Solinst file.
        """
        if type(data_file) == str:
            fid = open(data_file, 'r')

        else:
            fid = data_file

        fid = open(data_file)
        buf = fid.readline().strip('# ')
        while buf:
            if buf[0:8].lower() == 'datetime':
                params = buf.split(',')
                units = fid.readline().strip('# ').split(',')
                break

            key, val = buf.split(':')
            self.format_parameters[key.strip()] = val.strip()
            buf = fid.readline().strip('# ')

        utc_offset = int(
            self.format_parameters['timezone'].lower().strip('utc'))
        self.default_tzinfo = UTCStaticOffset(utc_offset)
        data = np.genfromtxt(fid, dtype=None, names=params, delimiter=',')
        self.dates = np.array(
            [datetime.datetime.strptime(dt, '%Y/%m/%d %H:%M:%S')
             for dt in data['datetime']]
            )

        #assign param & unit names
        for param, unit in zip(params[1:], units[1:]):
            self.num_params += 1
            self.parameters.append(Parameter(param.strip(), unit.strip()))

        for ii in range(self.num_params):
            param = self.parameters[ii].name
            self.parameters[ii].data = data[param]


class Parameter:
    """
    Class that implements the a structure to return a parameters
    name, unit and data
    """
    def __init__(self, param_name, param_unit):
        self.name = param_name
        self.unit = param_unit
        self.data = []
