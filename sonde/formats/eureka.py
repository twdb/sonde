"""
    sonde.formats.eureka
    ~~~~~~~~~~~~~~~~~

    This module implements the Eureka Manta format.
    The files may be in csv or Excel (xls) format

"""
from __future__ import absolute_import

import datetime
import os
import warnings

import numpy as np
import quantities as pq
import xlrd

from .. import sonde
from sonde import util
from sonde import quantities as sq


class EurekaDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a eureka cv or xls
    file. It accepts one optional parameters, `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.file_format = 'eureka'
        self.manufacturer = 'eureka'
        self.data_file = data_file
        self.default_tzinfo = tzinfo
        self.data = dict()
        self.dates = []
        super(EurekaDataset, self).__init__()

    def _read_data(self):
        """
        Read the eureka data file
        """
        param_map = {'Temp.': 'water_temperature',
                     'SC': 'water_specific_conductance',
                     'SAL': 'seawater_salinity',
                     'DO Sat': 'water_dissolved_oxygen_percent_saturation',
                     'DO SAT': 'water_dissolved_oxygen_percent_saturation',
                     'DO': 'water_dissolved_oxygen_concentration',
                     'pH': 'water_ph',
                     'Depth': 'water_depth_non_vented',
                     'Bat.': 'instrument_battery_voltage',
                     }

        unit_map = {'\xb0C': pq.degC,
                    '\xc2\xb0C': pq.degC,
                    '\xb0F': pq.degF,
                    '\xc2\xb0F': pq.degF,
                    'mS/cm': sq.mScm,
                    'uS/cm': sq.uScm,
                    '%Sat': pq.percent,
                    'mg/l': sq.mgl,
                    '': pq.dimensionless,
                    'm': sq.mH2O,
                    'V': pq.volt,
                    'psu': sq.psu,
                    }

        eureka_data = EurekaReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()

        for parameter in eureka_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]

                #ignore params that have no data
                if not np.all(np.isnan(parameter.data)):
                    self.parameters[pcode] = sonde.master_parameter_list[pcode]
                    self.data[param_map[parameter.name]] = parameter.data * \
                                                           punit
            except KeyError:
                warnings.warn('Un-mapped Parameter/Unit Type:\n'
                              '%s parameter name: "%s"\n'
                              '%s unit name: "%s"' %
                              (self.file_format, parameter.name,
                               self.file_format, parameter.unit),
                              Warning)

        self.format_parameters = {
            'header_lines': eureka_data.header_lines,
            }

        if hasattr(eureka_data, 'site_name'):
            self.site_name = eureka_data.site_name
        if hasattr(eureka_data, 'serial_number'):
            self.serial_number = eureka_data.serial_number
        if hasattr(eureka_data, 'setup_time'):
            self.setup_time = eureka_data.setup_time
        if hasattr(eureka_data, 'stop_time'):
            self.stop_time = eureka_data.stop_time

        self.dates = eureka_data.dates


class EurekaReader:
    """
    A reader object that opens and reads a Eureka csv/xls file.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.default_tzinfo = tzinfo
        self.header_lines = []
        self.parameters = []
        self.site_name = ''
        self.file_ext = data_file.split('.')[-1].lower()

        temp_file_path = None
        if self.file_ext == 'xls':
            temp_file_path, self.xlrd_datemode = util.xls_to_csv(data_file)
            file_buf = open(temp_file_path, 'rb')
        else:
            file_buf = open(data_file)

        try:
            self.read_eureka(file_buf)
        except:
            raise
        finally:
            file_buf.close()
            if temp_file_path:
                os.remove(temp_file_path)

        if tzinfo:
            if hasattr(self, 'setup_time'):
                self.setup_time = self.setup_time.replace(tzinfo=tzinfo)
            if hasattr(self, 'stop_time'):
                self.stop_time = self.stop_time.replace(tzinfo=tzinfo)

            self.dates = [i.replace(tzinfo=tzinfo) for i in self.dates]

    def read_eureka(self, data_file):
        """
        Open and read a Eureka file.
        """
        if type(data_file) == str:
            fid = open(data_file, 'r')
        else:
            fid = data_file
        self.read_data(fid)

    def read_data(self, fid):
        """
        Read header information
        """

        fid.seek(0)

        buf = fid.readline()

        while buf:
            if buf[0:4] == 'Date':
                break

            self.header_lines.append(buf)

            if 'Site Name' in buf:
                self.site_name = buf.split(',')[1].strip()
            if 'Serial Number' in buf:
                self.serial_number = buf.split(',')[1].strip()
            if 'Start time' in buf:
                d, t = buf.strip().split()[3:5]
                self.setup_time = datetime.datetime.strptime(
                    d + t, '%m/%d/%Y%H:%M:%S')
            if 'Stop time' in buf:
                d, t = buf.strip().split()[3:5]
                self.stop_time = datetime.datetime.strptime(
                    d + t, '%m/%d/%Y%H:%M:%S')

            buf = fid.readline()

        fields = buf.strip('\r\n').split(',')
        params = fields[2:]
        units = fid.readline().strip('\r\n').split(',')[2:]

        data = np.genfromtxt(fid, delimiter=',', dtype=None, names=fields)

        if self.file_ext == 'xls':  # xlrd reads in dates as floats
            self.dates = np.array(
                [(datetime.datetime(*xlrd.xldate_as_tuple(d, 0))
                  + datetime.timedelta(t))
                 for d, t in zip(data['Date'], data['Time'])]
                )
        else:
            self.dates = np.array(
                [datetime.datetime.strptime(d + t, '%m/%d/%Y%H:%M:%S')
                 for d, t in zip(data['Date'], data['Time'])]
                )

        #assign param & unit names
        for param, unit in zip(params, units):
            # grab serial number from the second 'Manta' field if it
            # exists
            if param.strip() == 'Manta':
                if 'Manta_1' in data.dtype.fields:
                    self.serial_number = data['Manta_1'][0].strip()

            elif param.strip() != '':  # remove trailing blank column
                if param == 'SAL':  # fix unitless Salinity column
                    unit = 'psu'

                self.parameters.append(Parameter(param.strip(), unit.strip()))

        # if the serial number just contains numbers the cell holding
        # it might be formatted as a number, in which case it gets
        # read in with a trailing '.0'
        if hasattr(self, 'serial_number') and \
               self.serial_number.rfind('.0') == len(self.serial_number) - 2:
            self.serial_number = self.serial_number[:-2]

        for ii in range(len(self.parameters)):
            param = (self.parameters[ii].name).strip(' .').replace(' ', '_')
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
