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
import os.path
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
from .. import util


class BadDatafileError(IOError):
    pass


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
        super(GreenspanDataset, self).__init__(data_file)

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
                     'TDS': 'water_total_dissolved_salts',
                     #'Redox': 'NotImplemented',
                     }

        unit_map = {'deg_C': pq.degC,
                    'Celcius': pq.degC,
                    'Celsius': pq.degC,
                    'deg_F': pq.degF,
                    'deg_K': pq.degK,
                    'ft': sq.ftH2O,
                    'mS/cm': sq.mScm,
                    'mg/l': sq.mgl,
                    'm': sq.mH2O,
                    'Metres': sq.mH2O,
                    'pH': pq.dimensionless,
                    'ppm': sq.mgl,
                    'psu': sq.psu,
                    'us/cm': sq.uScm,
                    'uS/cm': sq.uScm,
                    'volts': pq.volt,
                    'Volts': pq.volt,
                    'volt': pq.volt,
                    }

        greenspan_data = GreenspanReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = {}
        self.data = {}
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
                'log_file_name': greenspan_data.source_file_name\
                                .split('\\')[-1].split('.')[0],
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
        self.data = {}
        self.dates = []
        self.xlrd_datemode = 0
        if type(data_file) == str:
            self.file_name = data_file
        elif type(data_file) == file:
            self.file_name = data_file.name
        self.file_ext = self.file_name.split('.')[-1].lower()

        temp_file_path = None
        if self.file_ext == 'xls':
            temp_file_path, self.xlrd_datemode = util.xls_to_csv(self.file_name)
            file_buf = open(temp_file_path, 'rb')
        else:
            if type(data_file) == str:
                file_buf = open(data_file)
            elif type(data_file) == file:
                file_buf = data_file

        try:
            if not self.format_version:
                self.format_version = self.detect_format_version(file_buf)

            self.read_greenspan(file_buf)
        except:
            raise
        finally:
            file_buf.close()
            if temp_file_path:
                os.remove(temp_file_path)

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
            #from nose.tools import set_trace; set_trace()
            fid.readline()  # skip junk
            self.site_name = fid.readline().split(',')[1].rstrip(' \r\n')
            self.site_information = fid.readline().split(',')[1].rstrip(' \r\n')
            self.instrument_type = fid.readline().split(',')[-1].rstrip(' \r\n')
            self.serial_number = fid.readline().split(',')[1].rstrip('\x00\r\n')
            self.firmware_version = fid.readline().split(',')[1].rstrip('\r\n')
            self.top_of_case = fid.readline().split(',')[1].rstrip('\r\n')
            self.raingage = fid.readline().split(',')[1].rstrip(' \r\n')
            fid.readline()
            #column 0,1,2 = 'Data', 'dd/mm/yyyy hh:mm:ss', 'Type/Comment'
            #column [3:] = actual data
            fields = fid.readline().rstrip('\r\n').split(',')
            cols = range(len(fields))[3:]
            params = fields[3:]
            units = fid.readline().rstrip('\r\n').split(',')[3:]

            # skip Channel Number line
            fid.readline()

            #read data
            data_start = fid.tell()

            datestr = [line.split(',')[1] for line in fid]

            # xlrd reads in dates as floats, but excel isn't too
            # careful about datatypes and depending on how the file
            # has been handled, there's a chance that the dates have
            # already been converted to strings
            number_of_unique_dates = len(np.unique(np.array(
                [util.possibly_corrupt_xls_date_to_datetime(
                    dt, self.xlrd_datemode)
                 for dt in datestr])))

            self.dates = np.array((datetime.datetime(1900, 1, 1), ) \
                                  * number_of_unique_dates)

            for param, unit in zip(params, units):
                param_name, unit_name = param.strip('()_'), unit.strip('()_')

                # clean param & unit names
                self.parameters.append(Parameter(param_name,
                                                 unit_name))
                # initialize data dict with empty arrays
                self.data[param_name] = np.array((np.nan,) * len(self.dates))
            fid.seek(data_start)
            data_count = -1
            last_date = None
            for line in fid:
                line_split = line.split(',')
                date = util.possibly_corrupt_xls_date_to_datetime(
                    line_split[1])
                if date != last_date:
                    if last_date and date < last_date:
                        raise BadDatafileError(
                            "Non-sequential timestamps found in file '%s'. "
                            "This shouldn't happen!" % (fid.name,))

                    data_count += 1
                    self.dates[data_count] = date

                for i, parameter in enumerate(self.parameters, start=3):
                    val = line_split[i].strip()
                    if date == last_date:
                        if np.isnan(self.data[parameter.name][data_count]):
                            if val != '':
                                self.data[parameter.name][data_count] = \
                                                                      float(val)
                        elif val != '':
                            warnings.warn("Conflicting values for parameter "
                                          "'%s' on date: %s" % (
                                              parameter.name,
                                              self.dates[data_count]), Warning)
                            self.data[parameter.name][data_count] = float(val)
                    else:
                        if val == '':
                            self.data[parameter.name][data_count] = np.nan
                        else:
                            self.data[parameter.name][data_count] = float(val)

                last_date = date

            for ii, parameter in enumerate(self.parameters):
                self.parameters[ii].data = self.data[parameter.name]

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

        # if the serial number just contains numbers the cell holding
        # it might be formatted as a number, in which case it gets
        # read in with a trailing '.0'
        if hasattr(self, 'serial_number') and \
               self.serial_number.rfind('.0') == len(self.serial_number) - 2:
            self.serial_number = self.serial_number[:-2]


class Parameter:
    """
    Class that implements the a structure to return a parameters
    name, unit and data
    """

    def __init__(self, param_name, param_unit):
        self.name = param_name
        self.unit = param_unit
        self.data = []
