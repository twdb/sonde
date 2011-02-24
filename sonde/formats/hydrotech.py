"""
    sonde.formats.hydrotech
    ~~~~~~~~~~~~~~~~~

    This module implements the Hydrotech format
    There are two main hydrotech formats also
    the files may be in ASCII or Excel (xls) format
    The module attempts to autodetect the correct format

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

class HydrotechDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a hydrotech txt
    file. It takes one optional parameter `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the binary file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.manufacturer = 'hydrotech'
        self.data_file = data_file
        self.default_tzinfo = tzinfo
        super(HydrotechDataset, self).__init__()

    def _read_data(self):
        """
        Read the hydrotech data file
        """
        param_map = {'Temp' : 'TEM01',
                     'SpCond' : 'CON01',
                     'Sal' : 'SAL01',
                     'Dep25' : 'WSE01',
                     'IBatt' : 'BAT01',
                     }

        unit_map = {'\xf8C' : pq.degC,
                    'mS/cm' : sq.mScm,
                    'uS/cm' : sq.uScm,
                    'mg/l' : sq.mgl,
                    'meters' : sq.mH2O,
                    'Volts' : pq.volt,
                    'ppt' : sq.psu,
                    }

        hydrotech_data = HydrotechReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for parameter in hydrotech_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                #ignore params that have no data
                if not np.all(np.isnan(parameter.data)):
                    self.parameters[pcode] = sonde.master_parameter_list[pcode]
                    self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'Hydrotech Parameter Name:', parameter.name
                print 'Hydrotech Unit Name:', parameter.unit
                raise

        self.format_parameters = {
            'model' : hydrotech_data.model,
            'serial_number' : hydrotech_data.serial_number,
            'log_file_name' : hydrotech_data.log_file_name,
            'setup_time' : hydrotech_data.setup_time,
            'start_time' : hydrotech_data.start_time,
            'stop_time' : hydrotech_data.stop_time,
            'logging_interval' : hydrotech_data.logging_interval,
            'sensor_warmup_time' : hydrotech_data.sensor_warmup_time,
            'circltr_warmup_time' : hydrotech_data.circltr_warmup_time,
            }

        self.dates = hydrotech_data.dates

class HydrotechReader:
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
        file_buf = self.clean_file(data_file)
        self.read_hydrotech(file_buf, tzinfo)

    def clean_file(self, data_file):
        """
        Cleans input file by replacing # with 'NaN' and adding
        a # to the beginning of comment lines.
        Returns a StringIO object
        """
        fid = open(data_file)
        file_string = fid.read()
        #change no data string from # to NaN
        file_string = re.sub('#', 'NaN' , file_string)
        #remove quotes
        file_string = re.sub('"', '' , file_string)
        #prepend # to non data lines
        file_string = re.sub(re.compile('^(\D)',re.MULTILINE), '#\\1' , file_string)
        #remove junk binary characters

        return StringIO(file_string)

    def read_hydrotech(self, data_file, tzinfo=None):
        """
        Open and read a Hydrotech file.
        """
        if type(data_file) == str:
            fid = open(data_file, 'r')

        else:
            fid = data_file


        fid.seek(0)
        fmt = '%m%d%y%H%M%S'
        strp = '#,\r\n'

        buf = fid.readline().strip(strp)

        #remove junk binary at top of file
        if not 'MiniSonde' or 'Log File Name' in buf:
            buf = fid.readline().strip(strp)

        if 'MiniSonde' in buf:
            self.model, self.serial_number = buf.split()
            self.log_file_name = fid.readline().strip(strp).split(':')[-1].strip()

        else:
            self.log_file_name = buf.strip(strp).split(':')[-1].strip()

        d = fid.readline().strip(strp).split(':')[-1].strip()
        t = fid.readline().strip(strp).split(':')[-1].strip()
        self.setup_time = datetime.datetime.strptime(d+t, fmt)
        d = fid.readline().strip(strp).split(':')[-1].strip()
        t = fid.readline().strip(strp).split(':')[-1].strip()
        self.start_time = datetime.datetime.strptime(d+t, fmt)
        d = fid.readline().strip(strp).split(':')[-1].strip()
        t = fid.readline().strip(strp).split(':')[-1].strip()
        self.stop_time = datetime.datetime.strptime(d+t, fmt)
        interval = fid.readline().strip(strp).split(':')[-1].strip()
        sensor_warmup = fid.readline().strip(strp).split(':')[-1].strip()
        circltr_warmup = fid.readline().strip(strp).split(':')[-1].strip()
        self.logging_interval = int(interval[0:2])*3600 + int(interval[2:4])*60 + int(interval[4:6])
        self.sensor_warmup_time = int(sensor_warmup[0:2])*3600 + int(sensor_warmup[2:4])*60 + int(sensor_warmup[4:6])
        self.circltr_warmup_time = int(circltr_warmup[0:2])*3600 + int(circltr_warmup[2:4])*60 + int(circltr_warmup[4:6])

        buf = fid.readline().strip(strp)
        while buf[0:4]!='Date':
            buf = fid.readline().strip(strp)

        fields = buf.split(',')
        params = fields[2:]
        units = fid.readline().strip(strp).split(',')[2:]

        #read data
        fid.seek(0)

        #remove blank columns
        cols = []
        field_names = []
        ncol = 0
        for field in fields:
            if field!='':
                cols.append(ncol)
                field_names.append(field)

            ncol += 1


        data = np.genfromtxt(fid, delimiter=',', dtype=None, names=field_names, usecols = cols,  missing_values='NaN', filling_values=np.nan)

        if len(data['Date'][0].split('/')[-1])==2:
            fmt = '%m/%d/%y%H:%M:%S'
        else:
            fmt = '%m/%d/%Y%H:%M:%S'

        self.dates = np.array(
            [datetime.datetime.strptime(d + t, fmt)
             for d,t in zip(data['Date'],data['Time'])]
            )

        if tzinfo:
            self.setup_time = self.setup_time.replace(tzinfo=tzinfo)
            self.start_time = self.start_time.replace(tzinfo=tzinfo)
            self.stop_time = self.stop_time.replace(tzinfo=tzinfo)
            self.dates = [i.replace(tzinfo=tzinfo) for i in self.dates]

        for param,unit in zip(params,units):
            if param!='':
                self.num_params += 1
                self.parameters.append(Parameter(param, unit))

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
