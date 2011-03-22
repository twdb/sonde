"""
    sonde.formats.greenspan
    ~~~~~~~~~~~~~~~~~

    This module implements the Greenspan format
    There are two main greenspan formats also
    the files may be in ASCII or Excel (xls) format
    The module attempts to autodetect the correct format

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
from ..timezones import cdt, cst


class GreenspanDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a greenspan txt
    file. It accepts two optional parameters, `format` overides the
    autodetect algorithm that tries to detect the format automatically
    `tzinfo` is a datetime.tzinfo object that represents the timezone
    of the timestamps in the binary file.
    """

    def __init__(self, data_file, tzinfo=None, format_version=None):
        self.file_format = 'greenspan'
        self.manufacturer = 'greenspan'
        self.data_file = data_file
        self.format_version = format_version
        self.default_tzinfo = tzinfo
        super(GreenspanDataset, self).__init__()

    def _read_data(self):
        """
        Read the greenspan data file
        """
        param_map = {'Temperature': 'water_temperature',
                     'EC': 'water_electrical_conductivity',  # Double Check?
                     'EC Raw': 'water_electrical_conductivity',
                     'EC Norm': 'water_specific_conductance',
                     #'SpCond': 'water_specific_conductance???',
                     'Salinity': 'seawater_salinity',
                     #'DO % Sat': 'water_dissolved_oxygen_percent_saturation',
                     'DO': 'water_dissolved_oxygen_concentration',
                     'pH': 'water_ph',
                     'Pressure': 'water_depth_non_vented',
                     #'Level': 'water_depth_non_vented',
                     'Batt': 'instrument_battery_voltage',
                     'Battery': 'instrument_battery_voltage',
                     'TDS': 'TDS01',
                     #'Redox': 'NotImplemented',
                     }

        unit_map = {'deg_C': pq.degC,
                    'Celcius': pq.degC,
                    'Celsius': pq.degC,
                    'deg_F': pq.degF,
                    'deg_K': pq.degK,
                    'mS/cm': sq.mScm,
                    'uS/cm': sq.uScm,
                    'mg/l': sq.mgl,
                    'pH': pq.dimensionless,
                    'm': sq.mH2O,
                    'Metres': sq.mH2O,
                    'ft': sq.ftH2O,
                    'volts': pq.volt,
                    'Volts': pq.volt,
                    'volt': pq.volt,
                    'psu': sq.psu,
                    }

        greenspan_data = GreenspanReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for parameter in greenspan_data.parameters:
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

        if (greenspan_data.format_version == '2.4.1') or \
               (greenspan_data.format_version == '2.3.1'):
            self.format_parameters = {
                'converter_name': greenspan_data.converter_name,
                'source_file_name': greenspan_data.source_file_name,
                'target_file_name': greenspan_data.target_file_name,
                'site_information': greenspan_data.site_information,
                'firmware_version': greenspan_data.firmware_version,
                'top_of_case': greenspan_data.top_of_case,
                'raingage': greenspan_data.raingage,
                }

            self.serial_number = greenspan_data.serial_number
            self.site_name = greenspan_data.site_name

        elif greenspan_data.format_version == 'block':
            self.format_parameters = {
                'header_lines': greenspan_data.header_lines,
                }

        self.dates = greenspan_data.dates


class GreenspanReader:
    """
    A reader object that opens and reads a Hydrolab txt file.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """

    def __init__(self, data_file, tzinfo=None, format_version=None):
        self.default_tzinfo = tzinfo
        self.format_version = format_version
        self.num_params = 0
        self.parameters = []
        self.file_ext = data_file.split('.')[-1].lower()

        if self.file_ext == 'xls':
            file_buf = open(util.xls_to_csv(data_file), 'rb')
        else:
            file_buf = open(data_file, 'r')

        if not self.format_version:
            self.format_version = self.detect_format_version(file_buf)

        self.read_greenspan(file_buf)

        if tzinfo:
            self.dates = [i.replace(tzinfo=tzinfo) for i in self.dates]

    def detect_format_version(self, data_file):
        """
        Reads first several lines of file and tries to autodetect
        greenspan file format
        expects a file object
        """

        if type(data_file) == str:
            warnings.warn('Expects File Object', Warning)
        else:
            fid = data_file

        fid.seek(0)
        hdr = fid.readline()
        #file_ext = data_file.split('.')[-1]
        #if file_ext == 'xls':
        #    self.file_type = 'excel'
        #    wb = xlrd.open_workbook(data_file)
        #    sh = wb.sheet_by_index(0)
        #    hdr = sh.row_values(0)
        #    del wb
        #else:
        #    self.file_type = 'ascii'
        #    fid = open(data_file,'r')
        #    hdr = fid.readline()
        #    fid.close()

        if 'Greenspan data converter .dll Version:  2. 4. 1' in hdr:
            fmt = '2.4.1'
        elif 'Greenspan data converter .dll Version:  2. 3. 1' in hdr:
            fmt = '2.3.1'
        elif '# GREENSPAN' in hdr:
            fmt = 'block'
        else:
            fmt = 'unknown'

        return fmt

    def read_greenspan(self, data_file):
        """
        Open and read a Greenspan file.
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

        if (self.format_version == '2.4.1') or \
               (self.format_version == '2.3.1'):
            self.converter_name = fid.readline().split(',')[1].rstrip('\r\n')
            self.source_file_name = fid.readline().split(',')[2].rstrip('\r\n')
            self.target_file_name = fid.readline().split(',')[2].rstrip('\r\n')
            fid.readline()  # skip junk
            self.site_name = fid.readline().split(',')[-1].rstrip(' \r\n')
            self.site_information = fid.readline().split(',')[1].rstrip(' \r\n')
            self.instrument_type = fid.readline().split(',')[-1].rstrip(' \r\n')
            self.serial_number = fid.readline().split(',')[1].rstrip('\x00\r\n')
            self.firmware_version = fid.readline().split(',')[1].rstrip('\r\n')
            self.top_of_case = fid.readline().split(',')[1].rstrip('\r\n')
            self.raingage = fid.readline().split(',')[1].rstrip(' \r\n')
            fid.readline()
            #column 0,1,2 = 'Data', 'dd/mm/yyyy hh:mm:ss', 'Type/Comment'
            #column [3:] = actual data
            fid.readline()
            fields = fid.readline().rstrip('\r\n').split(',')
            cols = range(len(fields))[3:]
            params = fields[3:]
            units = fid.readline().rstrip('\r\n').split(',')[3:]

            #clean param & unit names
            for param, unit in zip(params, units):
                self.parameters.append(Parameter(param.strip('()_'),
                                                 unit.strip('()_')))

            #read data
            fid.seek(0)
            datestr = np.genfromtxt(fid, delimiter=',', skip_header=15,
                                    usecols=(1), dtype='|S')
            if self.file_ext == 'xls':  # xlrd reads in dates as floats
                self.dates = np.array(
                    [(datetime.datetime(*xlrd.xldate_as_tuple(dt, 0)))
                     for dt in datestr])
            else:
                self.dates = np.array(
                    [datetime.datetime.strptime(dt, '%d/%m/%Y %H:%M:%S')
                     for dt in datestr])


            fid.seek(0)
            self.data = np.genfromtxt(fid, delimiter=',', skip_header=15,
                                      usecols=cols, dtype=float)

            for ii in range(len(self.parameters)):
                self.parameters[ii].data = self.data[:, ii]

        elif self.format_version == 'block':

            self.header_lines = []
            self.header_lines.append(fid.readline())
            buf = fid.readline()
            self.header_lines.append(buf)
            buf = buf.strip('# \r\n')
            fmt = '%Y%m%d%H%M%S'
            self.start_time = datetime.datetime.strptime(buf[0:14], fmt)
            self.stop_time = datetime.datetime.strptime(buf[14:], fmt)

            buf = fid.readline()
            while buf:
                self.header_lines.append(buf)

                if buf[0] == 'T':
                    break

                if buf[0:4] == 'C0 B':
                    self.num_params += 1
                    param = 'Batt'
                    unit = 'volts'
                    self.parameters.append(Parameter(param.strip('()_'),
                                                     unit.strip('()_')))

                if buf[0:3] == '# C':
                    self.num_params += 1
                    unit, param = buf.split()[2:]
                    self.parameters.append(Parameter(param.strip('()_'),
                                                     unit.strip('()_')))

                buf = fid.readline()

            fmt = 'T%Y%m%d%H%M%S'
            dates = []
            data = []
            row = None
            prev_dt = None
            while buf:
                if buf[0] == 'T':
                    dt = datetime.datetime.strptime(buf.strip('\r\n'), fmt)
                    if dt != prev_dt:
                        prev_dt = dt
                        data.append(row)
                        dates.append(datetime.datetime.strptime(
                            buf.strip('\r\n'), fmt))
                        row = np.zeros(self.num_params)
                        row[:] = np.nan

                elif buf[0] == 'D':
                    col = int(buf[1])
                    row[col] = float(buf.split()[1])

                else:
                    self.header_lines.append(buf)

                buf = fid.readline()

                ### TODO WORK OUT HOW TO APPEND data.append(row) correctly
            #append last record to data
            data.append(row)
            #remove blank first record and convert to np.array
            data = np.array(data[1:])
            self.dates = np.array(dates)
            for ii in range(self.num_params):
                self.parameters[ii].data = data[:, ii]

        else:
            warnings.warn('Unknown Format Type', Warning)
            raise


class Parameter:
    """
    Class that implements the a structure to return a parameters
    name, unit and data
    """

    def __init__(self, param_name, param_unit):
        self.name = param_name
        self.unit = param_unit
        self.data = []
