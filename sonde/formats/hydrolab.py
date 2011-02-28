"""
    sonde.formats.hydrolab
    ~~~~~~~~~~~~~~~~~

    This module implements the Hydrolab format

"""
from __future__ import absolute_import

import datetime
import pkg_resources
import re
from StringIO import StringIO
import struct
import time

import numpy as np
import quantities as pq

from .. import sonde
from .. import quantities as sq
from ..timezones import cdt, cst

class HydrolabDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a Hydrolab txt
    file. It accepts two optional parameters, `param_file` is a
    ysi_param.def definition file and `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the
    binary file.
    """
    def __init__(self, data_file, tzinfo=None, param_file=None):
        self.file_format = 'hydrolab'
        self.manufacturer = 'hydrolab'
        self.data_file = data_file
        self.param_file = param_file
        self.default_tzinfo = tzinfo
        super(HydrolabDataset, self).__init__()


    def _read_data(self):
        """
        Read the Hydrolab txt data file
        """
        param_map = {'Temp' : 'water_temperature',
                     'Conductivity' : 'water_electrical_conductivity',
                     'SpCond' : 'water_specific_conductance',
                     'Salin' : 'seawater_salinity',
                     'DO % Sat' : 'water_dissolved_oxygen_percent_saturation',
                     'DO mg/l' : 'water_dissolved_oxygen_concentration',
                     'pH' : 'water_ph',
                     'Depth' : 'water_depth_non_vented',
                     'Level' : 'water_depth_non_vented',
                     'Batt' : 'instrument_battery_voltage',
                     'Turb' : 'water_turbidity',
                     'Redox': 'NotImplemented',
                     }

        unit_map = {'deg C' : pq.degC,
                    'deg F' : pq.degF,
                    'deg K' : pq.degK,
                    'mS/cm' : sq.mScm,
                    'uS/cm' : sq.uScm,
                    '% Sat' : pq.percent,
                    'mg/l' : sq.mgl,
                    'units' : pq.dimensionless,
                    'meters' : sq.mH2O,
                    'feet' : sq.ftH2O,
                    'volts' : pq.volt,
                    'ppt' : sq.psu,
                    'NTU' : sq.ntu,
                    'mV'  : 'NotImplemented',
                    }

        hydrolab_data = HydrolabReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for parameter in hydrolab_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                #ignore params that have no data
                if not np.all(np.isnan(parameter.data)):
                    self.parameters[pcode] = sonde.master_parameter_list[pcode]
                    self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'Hydrolab Parameter Name:', parameter.name
                print 'Hydrolab Unit Name:', parameter.unit
                raise

        self.format_parameters = {
            'log_file_name': hydrolab_data.log_file_name,
            'logging_interval': hydrolab_data.logging_interval,
            'header_lines': hydrolab_data.header_lines,
            }

        self.setup_time = hydrolab_data.setup_time
        self.start_time = hydrolab_data.start_time
        self.stop_time = hydrolab_data.stop_time

        self.dates = hydrolab_data.dates


class HydrolabReader:
    """
    A reader object that opens and reads a Hydrolab txt file.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.default_tzinfo = tzinfo
        self.num_params = 0
        self.parameters = []
        self.read_hydrolab(data_file)

        if tzinfo:
            self.setup_time = self.setup_time.replace(tzinfo=tzinfo)
            self.start_time = self.start_time.replace(tzinfo=tzinfo)
            self.stop_time = self.stop_time.replace(tzinfo=tzinfo)
            self.dates = [i.replace(tzinfo=tzinfo) for i in self.dates]


    def read_hydrolab(self, hydrolab_file):
        """
        Open and read a Hydrolab txt file.
        """
        if type(hydrolab_file) == str:
            fid = open(hydrolab_file, 'r')

        else:
            fid = hydrolab_file

        self.read_header(fid)
        self.read_data(fid)

    def read_header(self, fid):
        """
        Read header information
        """
        self.log_file_name = fid.readline().split(':')[-1].strip()
        setup_date = fid.readline().split(':')[-1].strip()
        setup_time = fid.readline().split(':')[-1].strip()
        start_date = fid.readline().split(':')[-1].strip()
        start_time = fid.readline().split(':')[-1].strip()
        stop_date = fid.readline().split(':')[-1].strip()
        stop_time = fid.readline().split(':')[-1].strip()
        interval = fid.readline().split(':')[-1].strip()
        self.warmup_status = fid.readline().split(':')[-1].strip()

        # convert to datetime. this assumes that date and time formats
        # are always MMDDYY & HHMMSS which is true for the sample of
        # files inspected
        fmt = '%m%d%y%H%M%S'
        self.setup_time = datetime.datetime.strptime(setup_date + setup_time, fmt)
        self.start_time = datetime.datetime.strptime(start_date + start_time, fmt)
        self.stop_time = datetime.datetime.strptime(stop_date + stop_time, fmt)
        self.logging_interval = int(interval[0:2])*3600 + int(interval[2:4])*60 + int(interval[4:6])
        self.header_lines = []

        #read variables and units.
        re_time = re.compile(' *Time')
        buf = fid.readline()
        while buf:
            if re_time.match(buf):
                allparams = buf
                params = buf.split()[1:]
                buf = fid.readline()
                # assumes fields are seperated by at least 2 spaces. single
                # spaces are assumed to be part of unit names
                # units = re.sub('\s{1,} ', ',', buf).split(',')[1:]
                # the above assumption fails on some files. new logic below
                # unit name ends at same column as param name ends.
                lbuf = list(buf.strip('\r\n'))
                loc = 0
                for param in allparams.split():
                    loc = allparams.find(param,loc) + len(param)
                    try:
                        lbuf[loc] = ','
                    except:
                        pass #last position
                units = "".join(lbuf).split(',')[1:]
                for param,unit in zip(params,units):
                    self.num_params += 1
                    if param=='DO':
                        name = param + ' ' + unit.strip()
                    else:
                        name = param

                    self.parameters.append(Parameter(name, unit))

                break
            else:
                self.header_lines.append(buf)
                buf = fid.readline()

    def read_data(self, fid):
        log_time = []
        fmt = '%m%d%y%H%M%S'
        data_str = ''
        re_date = re.compile(' *Date')
        re_data = re.compile('^[0-9]') # only process lines starting with a number

        # re_data = re.compile('((?!Date)(?![0-9]))', re.M) matches only junk lines
        # might be more efficient to work out how to use the above to strip out all
        # junk lines in one go.
        for buf in fid.readlines():
            if re_date.match(buf):
                log_date = buf.split(':')[-1].strip()

            if re_data.match(buf):
                try:
                    time_field, data_line = buf.split(None, 1)
                    log_time.append(datetime.datetime.strptime(log_date + time_field, fmt))
                    #fix for incomplete lines
                    if len(data_line.split()) < self.num_params:
                        data_line = data_line.strip('\r\n')
                        data_line += (self.num_params - len(data_line.split()))*' N ' + '\n'
                    data_str = data_str + data_line
                except:
                    continue

        self.dates = np.array(log_time)
        data_str = re.sub('#', 'N', data_str)
        data_str = re.sub('&', '', data_str)
        data_str = re.sub('@', '', data_str)
        data_str = re.sub('\*', '', data_str)
        try:
            data = np.genfromtxt(StringIO(data_str), dtype=float) 
        except:
            #no data in file
            print 'No Data Found In File'
            raise

        #de_duplicate data since some hydrolabs have repeat values
        self.dates, idx = np.unique(self.dates, return_index=True)
        data = data[idx]

        for ii in range(self.num_params):
            self.parameters[ii].data = data[:,ii]

class Parameter:
    """
    Class that implements the a structure to return a parameters
    name, unit and data
    """
    def __init__(self, param_name, param_unit):

        self.name = param_name
        self.unit = param_unit
        self.data = []
