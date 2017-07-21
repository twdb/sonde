"""
    sonde.formats.lcra
    ~~~~~~~~~~~~~~~~~

    This module implements an lcra format.
    the files are in .txt format and must conform to the
    following guidelines
    the first 10 lines are comments.The second line from last should have
    units.
    local timezone 
    fill_value = -99.9
     
    space separated data

    special columns or header items:
        original_data_file_name, instrument_manufacturer,
          instrument_serial_number
        if these exist they will overide self.manufacturer,
        self.data_file and self.serial_number

"""


import datetime
import pkg_resources
import warnings

import numpy as np
import quantities as pq
import pandas as pd

from .. import sonde
from .. import quantities as sq
from ..timezones import UTCStaticOffset

class LcraDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in 'lcra' txt
    file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.manufacturer = 'na'
        self.file_format = 'lcra'
        self.data_file = data_file
        self.default_tzinfo = tzinfo
        super(LcraDataset, self).__init__(data_file)

    def _read_data(self):
        """
        Read the sonde data file
        """
        #salinity used in some mw files was not consistent w/ what's calculated w/
        #seawater module used in pint. So not using it. SN
        param_map = {'temp': 'water_temperature',
             'pH': 'water_ph',
             'salinity': 'seawater_salinity',
             'cond': 'water_specific_conductance',  
             'D.O.': 'water_dissolved_oxygen_concentration',
             'level': 'water_depth_non_vented',
             'turbid': 'water_turbidity',
             }

        unit_map = {'C': pq.degC,
                    'mS/cm': sq.mScm,
                    'uS/cm': sq.uScm,
                    'psu': sq.psu,
                    '%': pq.percent,
                    'mg/l': sq.mgl,
                    'nd': pq.dimensionless,
                    'm': sq.mH2O,
                    'ft': sq.ftH2O,
                    'volts': pq.volt,
                    'ntu': sq.ntu
                    }

        lcra_data = LcraDataReader(
            self.data_file, tzinfo=self.default_tzinfo)
        self.parameters = dict()
        self.data = dict()
        metadata = dict()

        for parameter in lcra_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                self.parameters[pcode] = sonde.master_parameter_list[pcode]
                self.data[param_map[parameter.name]] = parameter.data * punit

            except KeyError:
                warnings.warn('Un-mapped Parameter/Unit Type:\n'
                              '%s parameter name: "%s"\n'
                              '%s unit name: "%s"' %
                              (self.file_format, parameter.name,
                               self.file_format, parameter.unit),
                              Warning)
            else:
                metadata[parameter.name.lower()] = parameter.data

        try:
            self.site_name = lcra_data.site_name
        except AttributeError:
            pass
        #overide default metadata if present in file
        names = ['manufacturer', 'data_file', 'serial_number']
        kwds = ['instrument_manufacturer', 'original_data_file',
                'instrument_serial_number']
        for name, kwd in zip(names, kwds):
            #check format_parameters
            idx = [i for i
                   in list(self.format_parameters.keys()) if i.lower() == kwd]
            if idx != []:
                exec('self.' + name + '=self.format_parameters[idx[0]]')
            idx = [i for i in list(metadata.keys()) if i.lower() == kwd]
            if idx != []:
                exec('self.' + name + ' = metadata[idx[0]]')

        self.dates = lcra_data.dates


class LcraDataReader:
    """
    A reader object that opens and reads wq files processed with older script.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.num_params = 0
        self.parameters = []
        self.format_parameters = {}
        self.default_tzinfo = tzinfo
        self.read_lcra(data_file)   
        
    def correct_time_string(self, int_time):
        if len(str(int_time)) == 1:
            return '000' + str(int_time)
        if len(str(int_time)) == 2:
            return '00' + str(int_time)
        if len(str(int_time)) == 3:
            return '0' + str(int_time)
        else:
            return str(int_time)
        
    def read_lcra(self, data_file):
        """
        Open and read an LC file.
        """
        if isinstance(data_file, str):
            fid = open(data_file, 'r')

        else:
            fid = data_file
            
        buf = 'header'
        while buf:
            buf = fid.readline()
            if buf.strip()[:2] == 'yr':
                columns = buf.strip().split()
                temp_units = fid.readline().strip().split()
                fid.readline() 
                break

        data = pd.read_csv(fid, sep='\s*', names=columns,
                           na_values='-9.99')
        data['yr'] = data['yr'].apply(lambda x: '200' + str(x) 
                                        if x < 10 else '19' + str(x))
        data['time'] = data['time'].apply(self.correct_time_string)                                    
                                    
#        import pdb; pdb.set_trace()
        raw_dates = np.array([datetime.datetime(int(y), m, d,int(str(t)[:2]), 
                                                int(str(t)[2:]),0)
                                for y, m, d, t
                               in zip(data['yr'].values, data['mo'].values,
                                      data['dy'].values, data['time'].values)])
        # remove records missing any of y,m,d,time parameters
        na_dates_mask = np.where(raw_dates != np.nan)[0]
        self.dates = raw_dates[na_dates_mask]
        params = columns[4:]
        units = temp_units[4:]
#        import pdb; pdb.set_trace()
        #assign param & unit names
        for param, unit in zip(params, units):
            self.num_params += 1
            self.parameters.append(Parameter(param.strip(), unit.strip()))

        for ii in range(self.num_params):
            param = self.parameters[ii].name
            self.parameters[ii].data = data[param].values[na_dates_mask]


class Parameter:
    """
    Class that implements the a structure to return a parameters
    name, unit and data
    """
    def __init__(self, param_name, param_unit):
        self.name = param_name
        self.unit = param_unit
        self.data = []
