"""
    sonde.formats.eureka
    ~~~~~~~~~~~~~~~~~

    This module implements the Eureka Manta format.
    The files may be in csv or Excel (xls) format

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

class EurekaDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a eureka cv or xls
    file. It accepts one optional parameters, `tzinfo` is a datetime.tzinfo
    object that represents the timezone of the timestamps in the file.
    """
    def __init__(self, data_file, tzinfo=None):
        self.data_file = data_file
        self.default_tzinfo = tzinfo
        super(EurekaDataset, self).__init__()


    def _read_data(self):
        """
        Read the eureka data file
        """
        param_map = {'Temp.' : 'TEM01',
                     'SC' : 'CON01',
                     'SAL' : 'SAL01',
                     'DO Sat' : 'DOX02',
                     'DO SAT' : 'DOX02',
                     'DO' : 'DOX01',
                     'pH' : 'PHL01',
                     'Depth' : 'WSE01',
                     'Bat.' : 'BAT01',
                     }

        unit_map = {'\xb0C' : pq.degC,
                    '\xc2\xb0C' : pq.degC,
                    '\xb0F' : pq.degF,
                    '\xc2\xb0F' : pq.degF,
                    'mS/cm' : sq.mScm,
                    'uS/cm' : sq.uScm,
                    '%Sat' : pq.percent,
                    'mg/l' : sq.mgl,
                    '' : pq.dimensionless,
                    'm' : sq.mH20,
                    'V' : pq.volt,
                    'psu' : sq.psu,
                    }

        eureka_data = EurekaReader(self.data_file, self.default_tzinfo)

        # determine parameters provided and in what units
        self.parameters = dict()
        self.data = dict()

        for parameter in eureka_data.parameters:
            try:
                pcode = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                #ignore params that have no data
                if not np.all(np.isnan(parameter.data)):
                    self.parameters[pcode] = sonde.master_parameter_list[pcode]
                    self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'Eureka Parameter Name:', parameter.name
                print 'Eureka Unit Name:', parameter.unit
                raise


        self.format_parameters = {
            'header_lines' : eureka_data.header_lines
            }

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
        self.num_params = 0
        self.parameters = []
        file_buf = StringIO()
        self.file_ext = data_file.split('.')[-1].lower()

        if self.file_ext =='xls':
            self.xls2csv(data_file, file_buf)
        else:
            file_buf.write(open(data_file).read())

        self.read_eureka(file_buf)


    def xls2csv(self, data_file, csv_file):
        """
        Converts excel files to csv equivalents
        assumes all data is in first worksheet
        """
        wb = xlrd.open_workbook(data_file)
        sh = wb.sheet_by_index(0)

        if type(csv_file) == str:
            bc = open(csv_file, 'w')

        else:
            bc = csv_file

        bcw = csv.writer(bc,csv.excel)

        for row in range(sh.nrows):
            this_row = []
            for col in range(sh.ncols):
                val = sh.cell_value(row, col)
                if isinstance(val, unicode):
                    val = val.encode('utf8')
                this_row.append(val)

            bcw.writerow(this_row)


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
        self.header_lines = []

        buf = fid.readline()

        while buf:
            if buf[0:4]=='Date':
                break

            self.header_lines.append(buf)
            buf = fid.readline()

        fields = buf.strip('\r\n').split(',')
        params = fields[2:]
        units = fid.readline().strip('\r\n').split(',')[2:]

        data = np.genfromtxt(fid, delimiter=',', dtype=None, names=fields)

        if self.file_ext=='xls': #xlrd reads in dates as floats
            self.dates = np.array(
                [(datetime.datetime(*xlrd.xldate_as_tuple(d,0)) +  datetime.timedelta(t))
                 for d,t in zip(data['Date'],data['Time'])]
                )
        else:
            self.dates = np.array(
                [datetime.datetime.strptime(d + t, '%m/%d/%Y%H:%M:%S')
                 for d,t in zip(data['Date'],data['Time'])]
                )

        #assign param & unit names
        for param,unit in zip(params,units):
            if param!='': #remove trailing blank column
                if param=='SAL': #fix unitless Salinity column
                    unit = 'psu'


                self.num_params += 1
                self.parameters.append(Parameter(param.strip(), unit.strip()))


        for ii in range(self.num_params):
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
