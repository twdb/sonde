"""
    sonde.formats.greenspan
    ~~~~~~~~~~~~~~~~~

    This module implements the Greenspan format
    There are two main greenspan formats also
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

class GreenspanDataset(sonde.BaseSondeDataset):
    """
    Dataset object that represents the data contained in a greenspan txt
    file. It accepts two optional parameters, `format` overides the
    autodetect algorithm that tries to detect the format automatically
    `tzinfo` is a datetime.tzinfo object that represents the timezone
    of the timestamps in the binary file.
    """
    def __init__(self, data_file, tzinfo=None, file_format=None):
        self.data_file = data_file
        self.file_format = file_format
        self.default_tzinfo = tzinfo
        super(GreenspanDataset, self).__init__()

    
    def _read_data(self):
        """
        Read the greenspan data file
        """
        param_map = {'Temperature' : 'TEM01',
                     'EC' : 'CON02', #Double Check?
                     'EC Raw' : 'CON02',
                     'EC Norm' : 'CON01',
                     
                     #'SpCond' : 'CON01???',
                     'Salinity' : 'SAL01',
                     #'DO % Sat' : 'DOX02',
                     'DO' : 'DOX01',
                     'pH' : 'PHL01',
                     'Pressure' : 'WSE01',
                     #'Level' : 'WSE01',
                     'Batt' : 'BAT01',
                     'TDS' : 'TDS01',
                     #'Redox': 'NotImplemented',
                     }
        
        unit_map = {'deg_C' : pq.degC,
                    'Celcius' : pq.degC,
                    'deg_F' : pq.degF,
                    'deg_K' : pq.degK,
                    'mS/cm' : sq.mScm,
                    'uS/cm' : sq.uScm,
                    #'% Sat' : pq.percent,
                    'mg/l' : sq.mgl,
                    #'ppm' : ,
                    'pH' : pq.dimensionless,
                    'm' : pq.m,
                    'Metres' : pq.m,
                    'ft' : pq.ft,
                    'volts' : pq.volt,
                    'volt' : pq.volt,
                    'psu' : sq.psu,
                    #'NTU' : sq.ntu,
                    #'mV'  : 'NotImplemented',
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
                    self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'Greenspan Parameter Name:', parameter.name
                print 'Greenspan Unit Name:', parameter.unit
                raise

        if (self.file_format == '2.4.1') or (self.file_format == '2.3.1'):
            self.format_parameters = {
                'converter_name' : greenspan_data.converter_name,
                'source_file_name' : greenspan_data.source_file_name,
                'target_file_name' : greenspan_data.target_file_name,
                'site_name' : greenspan_data.site_name,
                'site_information' : greenspan_data.site_information,
                'serial_number' : greenspan_data.serial_number,
                'firmware_version' : greenspan_data.firmware_version,
                'top_of_case' : greenspan_data.top_of_case,
                'raingage' : greenspan_data.raingage,
                }
            
        elif self.file_format == 'block':
            self.format_parameters = {
                'header_lines' : greenspan_data.header_lines
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
    def __init__(self, data_file, tzinfo=None, file_format=None):
        self.default_tzinfo = tzinfo
        self.file_format = file_format
        self.num_params = 0
        self.parameters = []
        file_buf = StringIO()
        file_ext = data_file.split('.')[-1]
        
        if file_ext =='xls':
            self.xls2csv(data_file, file_buf)
        else:
            file_buf.write(open(data_file).read())
            
        if not self.file_format:
            self.file_format = self.detect_file_format(file_buf)
            
        self.read_greenspan(file_buf)

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
        

    def detect_file_format(self, data_file):
        """
        Reads first several lines of file and tries to autodetect
        greenspan file format
        expects a file object
        """

        if type(data_file) == str:
            print 'Expects File Object'

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
        
        if (self.file_format == '2.4.1') or (self.file_format == '2.3.1'):

            self.converter_name = fid.readline().split(',')[1]
            self.source_file_name = fid.readline().split(',')[2]
            self.target_file_name = fid.readline().split(',')[2]
            self.site_name = fid.readline().split(',')[1]
            self.site_information = fid.readline().split(',')[1]
            self.serial_number = fid.readline().split(',')[1]
            self.firmware_version = fid.readline().split(',')[1]
            self.top_of_case = fid.readline().split(',')[1]
            self.raingage = fid.readline().split(',')[1]
            fid.readline()
            #column 0,1,2 = 'Data', 'dd/mm/yyyy hh:mm:ss', 'Type/Comment'
            #column [3:] = actual data
            fields = fid.readline().split(',')
            cols = range(len(fields))[3:]
            params = fields[3:]
            units = fid.readline().split(',')[3:]

            #clean param & unit names 
            for param,unit in zip(params,units):
                self.num_params += 1 
                self.parameters.append(Parameter(param.strip('()_'), unit.strip('()_')))

            #read data
            fid.seek(0)
            self.dates = np.genfromtxt(fid, delimiter=',', skiprows=15, usecols=(1), dtype=datetime.datetime)
            fid.seek(0)
            self.data = np.genfromtxt(fid, delimiter=',', skiprows=15, usecols=cols, dtype=float)

            for ii in range(self.num_params):
                self.parameters[ii].data = data[:,ii]

        elif self.file_format == 'block':

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

                if buf[0:3] == '# C':
                    self.num_params += 1
                    unit, param = buf.split()[2:] 
                    self.parameters.append(Parameter(param.strip('()_'), unit.strip('()_')))
                    
                buf = fid.readline()

            fmt = 'T%Y%m%d%H%M%S'            
            dates = []
            data = []
            row = None
            while buf:
                if buf[0] == 'T':
                    #if not row:
                    data.append(row) 
                    dates.append(datetime.datetime.strptime(buf.strip('\r\n'), fmt))
                    row = np.zeros(self.num_params)
                    row[:] = np.nan 

                elif buf[0]  == 'D':
                    col = int(buf[1]) - 1
                    row[col] = float(buf.split()[-1])

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
                self.parameters[ii].data = data[:,ii]
           
        else:
            print 'Unknown Format Type'
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
