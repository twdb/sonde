"""
    sonde.formats.macroctd
    ~~~~~~~~~~~~~~~~~

    This module implements the Macroctd Manta format.
    The files may be in csv or Excel (xls) format

"""
from __future__ import absolute_import

import datetime
import pkg_resources

import numpy as np
import quantities as pq

from .. import sonde
from .. import quantities as sq
from ..timezones import cdt, cst

class MacroctdDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a macroctd cv or xls
    file. It accepts one optional parameters, `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.file_format = 'macroctd'
        self.data_file = data_file
        self.default_tzinfo = tzinfo
        super(MacroctdDataset, self).__init__()


    def _read_data(self):
        """
        Read the macroctd data file
        """
        param_map = {'Temperature' : 'water_temperature',
                     'EC' : 'water_electrical_conductivity',
                     'Pressure' : 'water_depth_non_vented',
                     'Battery' : 'instrument_battery_voltage',
                     }

        unit_map = {'degC' : pq.degC,
                    'mS/cm' : sq.mScm,
                    'psi' : pq.psi,
                    'volts' : pq.volt,
                    }

        macroctd_data = MacroctdReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for parameter in macroctd_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                #ignore params that have no data
                if not np.all(np.isnan(parameter.data)):
                    self.parameters[pcode] = sonde.master_parameter_list[pcode]
                    self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'Macroctd Parameter Name:', parameter.name
                print 'Macroctd Unit Name:', parameter.unit
                raise


        self.format_parameters = {
            'header_lines' : macroctd_data.header_lines,
            'serial_number' : macroctd_data.serial_number,
            'site_name' : macroctd_data.site_name,
            }

        self.dates = macroctd_data.dates

class MacroctdReader:
    """
    A reader object that opens and reads a Macroctd txt file.

    `data_file` should be either a file path string or a file-like
    object. It accepts one optional parameter, `tzinfo` is a
    datetime.tzinfo object that represents the timezone of the
    timestamps in the txt file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.default_tzinfo = tzinfo
        self.num_params = 0
        self.parameters = []
        self.read_macroctd(data_file)

        if tzinfo:
            self.dates = [i.replace(tzinfo=tzinfo) for i in self.dates]


    def read_macroctd(self, data_file):
        """
        Open and read a Macroctd file.
        """

        fid = open(data_file)
        self.header_lines = []

        buf = fid.readline()
        self.header_lines.append(buf)
        buf = fid.readline()
        self.header_lines.append(buf)
        self.serial_number = buf.split(',')[3]

        while buf:
            if buf[0:9]=='@AVERAGES':
                break

            if buf[0:11]=='@DEPLOYMENT':
                self.site_name = buf.split(None,1)[-1].strip('"\r\n')

            self.header_lines.append(buf)
            buf = fid.readline()

        fields = ['Date', 'Time', 'Battery', 'Temperature', 'EC', 'Pressure']
        params = fields[2:]
        units = ['volts', 'degC', 'mS/cm', 'psi']

        data = np.genfromtxt(fid, delimiter=',', dtype=None, names=fields)

        self.dates = np.array(
            [datetime.datetime.strptime(d + t, '%m/%d/%y%H:%M')
             for d,t in zip(data['Date'],data['Time'])]
            )

        #atm pressure correction for macroctd
        data['Pressure'] -= 14.7
        #assign param & unit names
        for param,unit in zip(params,units):
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
