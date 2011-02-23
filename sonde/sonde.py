"""
    sonde.Sonde
    ~~~~~~~~~~~

    This module implements the main Sonde object.

"""
from __future__ import absolute_import

import datetime
from exceptions import NotImplementedError
import re

import numpy as np
import os
import quantities as pq
import pytz
import seawater.csiro
import xlrd
import csv
from StringIO import StringIO

from sonde import quantities as sq
from sonde.timezones import cst,cdt


#XXX: put this into a proper config file
#: The default timezone to use when reading files
default_timezone = cst


#: A dict that contains all the parameters that could potentially be
#: read from a data file, along with their standard units. This list
#: is exhaustive and will be fully populated whether or not data is or
#: even available in a particular format. See the `parameters`
#: attribute for parameters that are available for a particular file.
master_parameter_list = {
    'ATM01' : ('Atmospheric Pressure', pq.pascal),
    'BAT01' : ('Battery Voltage', pq.volt),
    'CON01' : ('Specific Conductance(Normalized @25degC)', sq.mScm),
    'CON02' : ('Conductivity(Not Normalized)', sq.mScm),
    'DOX01' : ('Dissolved Oxygen Concentration', sq.mgl),
    'DOX02' : ('Dissolved Oxygen Saturation Concentration', pq.percent),
    'PHL01' : ('pH Level', pq.dimensionless),
    'SAL01' : ('Salinity', sq.psu),
    'TEM01' : ('Water Temperature', pq.degC),
    'TEM02' : ('Air Temperature', pq.degC),
    'TUR01' : ('Turbidity', sq.ntu),
    'WSE01' : ('Water Surface Elevation (No Atm Pressure Correction)', sq.mH2O),
    'WSE02' : ('Water Surface Elevation (Atm Pressure Corrected)', sq.mH2O),
    }



def Sonde(data_file, file_format=None , *args, **kwargs):
    """
    Read `data_file` and create a sonde dataset instance for
    it. `data_file` must be either a file path string or a file-like
    object. `file_format` should be a string containing the format
    that the file is in. if `file_format` not provided function will
    try to autodetect format.

    Currently supported file formats are:
      - `ysi`: a YSI binary file
      - `hydrolab`: a Hydrolab txt file
      - `greenspan`: a Greenspan txt/csv/xls file
      - `eureka` : a Eureka Manta xls/csv file
      - `macroctd` : a Macroctd csv file
      - `hydrotech` : a Hydrotech csv file
      - `solinst` : a solinst lev file

    """

    if not file_format:
        file_format = autodetect(data_file)

    if file_format.lower() == 'ysi':
        from sonde.formats.ysi import YSIDataset
        return YSIDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'hydrolab':
        from sonde.formats.hydrolab import HydrolabDataset
        return HydrolabDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'greenspan':
        from sonde.formats.greenspan import GreenspanDataset
        return GreenspanDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'eureka':
        from sonde.formats.eureka import EurekaDataset
        return EurekaDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'macroctd':
        from sonde.formats.macroctd import MacroctdDataset
        return MacroctdDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'hydrotech':
        from sonde.formats.hydrotech import HydrotechDataset
        return HydrotechDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'solinst':
        from sonde.formats.solinst import SolinstDataset
        return SolinstDataset(data_file, *args, **kwargs)

    if file_format == False:
        print "File Format Autodetection Failed"
        raise

    else:
        raise NotImplementedError, "file format '%s' is not supported" % \
                                   (file_format,)

def autodetect(data_file):
    """
    autodetect file_format based on file
    return file_format string if successful or
    False if unable to determine format
    """

    fid = StringIO()
    file_ext = data_file.split('.')[-1].lower()

    if file_ext=='xls':
        xls2csv(data_file, fid)
    else:
        fid.write(open(data_file).read())

    fid.seek(0)

    #read first line
    line1 = fid.readline()

    if line1.lower().find('greenspan')!=-1:
        return 'greenspan'

    if line1.lower().find('macrocdt')!=-1:
        return 'macroctd'

    if line1.lower().find('minisonde4a')!=-1:
        return 'hydrotech'

    if line1.lower().find('data file for datalogger.')!=-1:
        return 'solinst'

    if line1.lower().find('log file name')!=-1:
        return 'hydrolab'

    #read second line
    line2 = fid.readline()

    if line2.lower().find('log file name')!=-1: #binary junk in first line
        return 'hydrotech'

    #check for ysi
    if line1[0]=='A':
        return 'ysi' #binary

    if line1.find('=')!=-1:
        return 'ysi' #txt file

    if file_ext=='cdf':
        return 'ysi' #cdf file

    #eureka try and detect degree symbol
    #print line2
    if line2.find('\xb0')!=-1:
        return 'eureka'

    else:
        return False



def xls2csv(data_file, csv_file):
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

def merge(file_list, tz_list=None):
    """
    Merges all files in file_list
    tz_list specifies timezone of each file. 
    If tz_list == None then cst is assumed i.e UTC-6
    """
    if tz_list is None:
        tz_list = [cdt for fn in file_list]

    data = dict()
    data['dates'] = np.empty(0,dtype=datetime.datetime)
    data['filenames'] = np.empty(0,dtype='|S100')
    for param,unit in master_parameter_list.items():
        data[param] = np.empty(0, dtype='<f8')*unit[-1]

    for file_name, tz in zip(file_list, tz_list):
        print 'processing: ', file_name
        dataset = Sonde(file_name, tzinfo=tz)
        data['dates'] = np.hstack((data['dates'],dataset.dates))
        fnames = np.zeros(dataset.dates.size, dtype='|S100')
        fnames[:] = os.path.split(file_name)[-1]
        data['filenames'] = np.hstack((data['filenames'],fnames))
        no_data = np.zeros(dataset.dates.size)
        no_data[:] = np.nan
        for param in master_parameter_list.keys():
            if param in dataset.data.keys():
                tmp_data = dataset.data[param]
            else:
                tmp_data = no_data

            data[param] = np.hstack((data[param],tmp_data))

    for param,unit in master_parameter_list.items():
        if np.all(np.isnan(data[param])):
            del data[param]
        else:
            data[param] = data[param]*unit[-1]

    return data

class BaseSondeDataset(object):
    """
    The base class that all sonde format objects should inherit. This
    class contains all the attributes and methods that are common to
    all data formats; it is not intended to be instantiated directly.
    """
    #: A dict that maps parameter codes to long descriptions and their
    #: standard units
    parameters = {}

    def __init__(self):
        self.format_parameters = {}
        self._read_data()
        self.rescale_all()

        if 'CON01' in self.data or 'CON02' in self.data:
            self._calculate_salinity()

        #if 'site_name' in self.format_parameters.keys():
        #    site_name = self.format_parameters['site_name']
        #    @todo tz check

        if default_timezone and self.dates[0].tzinfo != None:
            self.convert_timezones(default_timezone)

        if 'setup_time' not in self.format_parameters.keys() :
            self.format_parameters['setup_time'] = self.dates[0]

        if 'start_time' not in self.format_parameters.keys() :
            self.format_parameters['start_time'] = self.dates[0]

        if 'stop_time' not in self.format_parameters.keys() :
            self.format_parameters['stop_time'] = self.dates[-1]

        #TODO ADD COMMENTS FIELD


    def get_standard_unit(self, param_code):
        """
        Return the standard unit for given parameter `param_code`
        """
        return self.parameters[param_code][1]


    def set_standard_unit(self, param_code, param_unit):
        """
        Set the standard param_unit for a given parameter `param_code`
        to `param_unit`. This method automatically rescales the data
        to the standard unit.
        """
        if param_code in self.parameters:
            param_description = self.parameters[param_code][0]
        else:
            param_description = master_parameter_list[param_code][0]

        self.parameters[param_code] = (param_description, param_unit)

        if param_code in self.data:
            self.rescale_parameter(param_code)


    def rescale_all(self):
        """
        Cycle through the parameter list and convert all data values
        to their standard units.
        """
        for param_code in self.parameters.keys():
            self.rescale_parameter(param_code)


    def rescale_parameter(self, param_code):
        """
        Convert the data for a parameter to its standard unit.
        """
        std_unit = self.get_standard_unit(param_code)
        current_unit = self.data[param_code].units

        # return if dimensionless parameter
        if not len(std_unit.dimensionality.keys()):
            return

        # XXX: Todo: Fix upstream (see comment in _temperature_offset)
        std_symbol = std_unit.dimensionality.keys()[0].symbol
        current_symbol = current_unit.dimensionality.keys()[0].symbol

        #if current_unit != std_unit:
        if current_symbol != std_symbol:
            self.data[param_code] = self.data[param_code].rescale(std_unit)

            # Add temperature offset depending on the temperature scales
            if isinstance(std_unit, pq.UnitTemperature):
                self.data[param_code] += self._temperature_offset(current_unit, std_unit)


    def _temperature_offset(self, from_unit, to_unit):
        """
        Return the offset in degrees of `to_unit` that should be
        applied when converting from quantities units `from_unit` to
        `to_unit`. The quantities package purposely avoids converting
        absolute temperature scales to avoid ambiguity.
        """

        # This looks is a bit hacky because it is. In the quantities
        # package, comparing the units for celcius and kelvin
        # evaluates to true because it only considers relative
        # temperatures. We need to compare the symbol string. We
        # should talk to the quantities maintainers and see if we can
        # come up with a cleaner way to do this.
        from_symbol = from_unit.dimensionality.keys()[0].symbol
        to_symbol = to_unit.dimensionality.keys()[0].symbol

        if from_symbol == to_symbol:
            return np.array([0]) * to_unit

        elif from_symbol == 'degC' and to_symbol == 'degF':
            return 32 * pq.degF

        elif from_symbol == 'degC' and to_symbol == 'K':
            return 273.15 * pq.degK

        elif from_symbol == 'degF' and to_symbol == 'degC':
            return -(32*(5.0/9)) * pq.degC

        elif from_symbol == 'degF' and to_symbol == 'K':
            return 459.67 * (5.0/9) * pq.degK

        elif from_symbol == 'K' and to_symbol == 'degC':
            return -273.15 * pq.degC

        elif from_symbol == 'K' and to_symbol == 'degF':
            return -459.67 * pq.degF

        else:
            raise NotImplementedError, "conversion from %s to %s not supported" % (from_symbol, to_symbol)


    def _calculate_salinity(self):
        """
        Calculate salinity if salinity parameter is missing but
        conductivity is present.
        """
        params = self.parameters.keys()
        if 'SAL01' in params:
            return
        else:
            if 'CON01' in params:
                T = 25.0
                cond = self.data['CON01'].rescale(sq.mScm).magnitude
            elif 'CON02' in params:
                current_unit = self.data['TEM01'].units
                temp_celsius = self.data['TEM01'].rescale(pq.degC)
                temp_celsius += self._temperature_offset(current_unit, pq.degC)
                T = temp_celsius.magnitude
                cond = self.data['CON02'].rescale(sq.mScm).magnitude
            else:
                return

            # absolute pressure in dbar
            #if 'WSE01' in params:
            #    P = self.data['WSE01'].rescale(pq.m).magnitude * 1.0197 + 10.1325
            #elif 'WSE02' in params:
            #    P = self.data['WSE02'].rescale(pq.m).magnitude * 1.0197
            #else:
            #    P = 10.1325

            if 'WSE01' in params:
                P = self.data['WSE01'].rescale(sq.dbar).magnitude + (pq.atm).rescale(sq.dbar).magnitude
            elif 'WSE02' in params:
                P = self.data['WSE02'].rescale(sq.dbar).magnitude
            else:
                P = (pq.atm).rescale(dbar).magnitude

            R = cond / 42.914
            sal = seawater.csiro.salt(R,T,P)

            self.set_standard_unit('SAL01', sq.psu)
            self.data['SAL01'] = sal * sq.psu


    def convert_timezones(self, to_tzinfo):
        """
        Convert all dates to some timezone. The argument `to_tzinfo`
        must be an instance of datetime.tzinfo, either from the
        datetime library itself or the pytz library.
        """

        # If to_tzinfo is a pytz timezone, then use the normalize
        # method so pytz can do normalize DST transition data
        if isinstance(to_tzinfo, pytz.tzinfo.BaseTzInfo):
            self.dates = np.array([to_tzinfo.normalize(date.astimezone(to_tzinfo))
                                   for date in self.dates])

        # If to_tzinfo is a regular tz_info instance, then just call
        # astimezone
        else:
            self.dates = np.array([date.astimezone(to_tzinfo)
                                   for date in self.dates])


    def _read_data(self):
        """
        Read data from a file. This method should be implemented by
        each format module.
        """
        return [np.array([]),np.array([])]
