"""
    sonde.formats.ysi
    ~~~~~~~~~~~~~~~~~

    This module implements the YSI format 
    
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


DEFAULT_YSI_PARAM_DEF = 'data/ysi_param.def'


class YSIDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a YSI binary
    file. It accepts two optional parameters, `param_file` is a
    ysi_param.def definition file and `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the
    binary file.
    """
    def __init__(self, data_file, tzinfo=None, param_file=None):
        self.data_file = data_file
        self.param_file = param_file
        self.default_tzinfo = tzinfo
        super(YSIDataset, self).__init__()

    
    def _read_data(self):
        """
        Read the YSI binary data file
        """
        param_map = {'Temperature' : 'TEM01',
                     'Conductivity' : 'CON02',
                     'Specific Cond' : 'CON01',
                     'Salinity' : 'SAL01',
                     'DO+' : 'DOX02',
                     'pH' : 'PHL01',
                     'Depth' : 'WSE01',
                     'Battery' : 'BAT01',
                     }

        unit_map = {'C' : pq.degC,
                    'F' : pq.degF,
                    'K' : pq.degK,
                    'mS/cm' : sq.mScm,
                    'uS/cm' : sq.uScm,
                    '%' : pq.percent,
                    'pH' : pq.dimensionless,
                    'meters' : pq.m,
                    'feet' : pq.ft,
                    'volts' : pq.volt,
                    }


        ysi_data = YSIReader(self.data_file, self.default_tzinfo, self.param_file)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()
        for parameter in ysi_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                self.parameters[pcode] = sonde.master_parameter_list[pcode]
                self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'YSI Parameter Name:', parameter.name
                print 'YSI Unit Name:', parameter.unit
                raise

        self.dates = ysi_data.dates



class ChannelRec:
    """
    Class that implements the channel record data structure used by
    the YSI binary file format
    """
    def __init__(self, rec, param_def):
        self.sonde_channel_num = rec[0]
        self.sensor_type = rec[1]
        self.probe_type = rec[2]
        self.zero_scale = rec[3]
        self.full_scale = rec[4]
        self.name = param_def[rec[1]][1]
        self.unit = param_def[rec[1]][2]
        self.unitcode = param_def[rec[1]][3]
        self.ndecimals = param_def[rec[1]][4]
        self.data = []



class YSIReader:
    """
    A reader object that opens and reads a YSI binary file.
    
    `data_file` should be either a file path string or a file-like
    object. It accepts two optional parameters, `param_file` is a
    ysi_param.def definition file and `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the
    binary file.
    """
    def __init__(self, data_file, tzinfo=None, param_file=None):
        self.default_tzinfo = tzinfo
        self.num_params = 0
        self.parameters = []
        self.julian_time = []
        self.read_param_def(param_file)
        self.read_ysi(data_file)

        ysi_epoch = datetime.datetime(year=1984, month=3, day=1,
                                      tzinfo=tzinfo)

        ysi_epoch_in_seconds = time.mktime(ysi_epoch.timetuple())
                                                    
        for param in self.parameters:
            param.data = (np.array(param.data)).round(decimals=param.ndecimals)
            
        self.dates = np.array([datetime.datetime.fromtimestamp(t + ysi_epoch_in_seconds, tzinfo)
                               for t in self.julian_time])

        self.julian_time = np.array(self.julian_time)
        self.begin_log_time = datetime.datetime.fromtimestamp(self.begin_log_time + ysi_epoch_in_seconds)
        self.first_sample_time = datetime.datetime.fromtimestamp(self.first_sample_time + ysi_epoch_in_seconds)


    def read_param_def(self, param_file):
        """
        Open and read a YSI param definition file.
        """
        if param_file == None:
            file_string = pkg_resources.resource_string('sonde',
                                                        DEFAULT_YSI_PARAM_DEF)
        elif type(param_file) == str:
            with open(param_file) as fid:
                file_string = fid.read()

        elif type(param_file) == file:
            file_string = param_file.read()
    
        file_string = re.sub("\n\s*\n*", "\n", file_string) #remove blank lines
        file_string = re.sub(";.*\n*", "", file_string)     #remove comment lines
        file_string = re.sub("\t", "", file_string)         #remove tabs
        file_string = re.sub("\"", "", file_string)         #remove quotes
        self.ysi_file_version = int(file_string.splitlines()[0].split('=')[-1])
        self.ysi_num_param_in_def = int(file_string.splitlines()[1].split('=')[-1])
        self.ysi_ecowatch_version = int(file_string.splitlines()[2].split('=')[-1])
        dtype = np.dtype([('ysi_id', '<i8'),
                          ('name', '|S20'),
                          ('unit', '|S11'),
                          ('shortname', '|S9'),
                          ('num_dec_places', '<i8')])
        self.ysi_param_def = np.genfromtxt(StringIO(file_string), delimiter=',', usecols=(0,1,3,5,7) , skip_header=3, dtype=dtype)
        

    def read_ysi(self, ysi_file):
        """
        Open and read a YSI binary file.
        """
        if type(ysi_file) == str:
            fid = open(ysi_file)

        else:
            fid = ysi_file
            
        record_type = []
        self.num_params=0

        record_type = fid.read(1)
        while record_type:

            if record_type == 'A':
                fmt = '<HLH16s32s6sLll36s'
                fmt_size = struct.calcsize(fmt)
                self.instr_type, self.system_sig, self.prog_ver, \
                                 self.serial_num, self.site_name, self.pad1,\
                                 self.logging_interval, self.begin_log_time, \
                                 self.first_sample_time, self.pad2 \
                                 = struct.unpack(fmt, fid.read(fmt_size))

            elif record_type == 'B':
                self.num_params = self.num_params + 1
                fmt = '<hhHff'
                fmt_size = struct.calcsize(fmt)
                self.parameters.append(ChannelRec(struct.unpack(fmt, fid.read(fmt_size)), self.ysi_param_def))

            elif record_type == 'D':
                fmt = '<l' + str(self.num_params) + 'f'
                fmt_size = struct.calcsize(fmt)
                recs = struct.unpack(fmt, fid.read(fmt_size))
                self.julian_time.append(recs[0])
                for ii in range(self.num_params):
                    self.parameters[ii].data.append(recs[ii+1])

            else:
                print 'Type not implemented yet:', record_type
                break

            record_type = fid.read(1)


        if type(ysi_file) == str:
            fid.close()
