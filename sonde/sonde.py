"""
    sonde.Sonde
    ~~~~~~~~~~~

    This module implements the main Sonde object.
    
"""

from __future__ import absolute_import

import datetime
import numpy as np
import quantities as pq
import pytz
import re
import seawater

from . import quantities as sq
#import logging
from .timezones import cst

# XXX: put this into a proper config file
default_timezone = cst


class Sonde(object):
    """The main Sonde class that all data format objects inherit. The
    Sonde object is not intended to be instantiated directly; this
    class contains all the attributes and methods that are common to
    all data formats.
    """

    def __init__(self):
        #: A dict that contains all the parameters that could
        #: potentially be read from a data file, along with their
        #: standard units. This list is exhaustive and will be fully
        #: populated whether or not data is or even available in a
        #: particular format. See the `parameters` attribute for
        #: parameters that are available for a particular file.
        self.master_parameter_list = {'TEM01' : ('Water Temperature', pq.degC),
                                      'CON01' : ('Specific Conductance(Normalized @25degC)', sq.mScm),
                                      'CON02' : ('Conductivity(Not Normalized)', sq.mScm),
                                      'SAL01' : ('Salinity', sq.psu),
                                      'WSE01' : ('Water Surface Elevation (No Atm Pressure Correction)', pq.m),
                                      'WSE02' : ('Water Surface Elevation (Atm Pressure Corrected)', pq.m),
                                      'BAT01' : ('Battery Voltage', pq.volt),
                                      'PHL01' : ('pH Level', pq.dimensionless),
                                      'DOX01' : ('Dissolved Oxygen Concentration', sq.mgl),
                                      'DOX02' : ('Dissolved Oxygen Saturation Concentration', pq.percent),
                                      'ATM01' : ('Atmospheric Pressure', pq.pascal),
                                      'TEM02' : ('Air Temperature', pq.degC),
                                      'TUR01' : ('Turbidity', sq.ntu),
                                      }

        #: A dict containing the parameters read from a data file and
        #: their values
        self.parameters = {}

        self.read_data()
        self.normalize_data()

        if default_timezone:
            self.convert_timezones(default_timezone)

        #self.remove_abnormal_ECNorm()
        #self.convert_data_to_common_fmt()
        #TODO ADD COMMENTS FIELD

    
    def get_standard_unit(self,code):
        """Returns the standard unit for given parameter `code`"""
        return self.master_parameter_list[code][1]

    def set_standard_unit(self, code, unit):
        """Sets the standard unit for a given parameter `code` to `unit`"""
        self.parameters[code][1] = unit

    def normalize_data(self):
        """Cycles through the parameter list and normalizes all data
        values to their standard units."""
        self.available_params_orig = self.parameters.copy()

        new_params = dict()
        for param, unit in self.parameters.iteritems():
            std_unit = self.get_standard_unit(param)
            if unit == std_unit:
                new_params[param] = unit
                continue
            else:
                new_params[param] = std_unit
                self.data[param] = self.data[param].rescale(std_unit)
                if param[0:3] == 'TEM': #assumes TEMP is in degF
                    self.data[param] = 32 * pq.degC + self.data[param]             

        self.parameters = new_params
            
    def calculate_salinity(self):
        """Calculates salinity if salinity parameter is missing but
        conductivity is present. This method assumes that conductivity
        parameters are in standard units (i.e. :attr:`convert_to_stdunits`
        has been run).
        """
        params = self.parameters.keys()
        if 'SAL01' in params:
            return
        else:
            if 'CON01' in params:
                T = 25.0
                cond = self.data['CON01'].magnitude
            elif 'CON02' in params:
                T = self.data['TEM01'].magnitude
                cond = self.data['CON02'].magnitude
            else:
                return
            
            #absolute pressure in dbar
            if 'WSE01' in params:
                P = self.data['WSE01'].magnitude * 1.0197 + 10.1325
            elif 'WSE02' in params:
                P = self.data['WSE02'].magnitude * 1.0197 
            else:
                P = 10.1325
            
            R = cond / 42.914
            sal = seawater.salt(R,T,P)

            #add salinity to list of available params
            self.parameters['SAL01'] = sq.psu
            self.data['SAL01'] = sal * sq.psu

    def convert_timezones(self, to_tzinfo):
        """
        Converts all dates to some timezone. The argument `to_tzinfo`
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

    def read_data(self):
        """Reads data from a file. This method should be implemented
        by each format module."""
        return [np.array([]),np.array([])]

    def write_data_to_file(self, split=True):
        """Writes data to a file. 
        If split=True then write one file per parameter. If split=False write a single merged file
        """
        prefix = self.filename.split('.')[0]
        if split:
            for key in np.sort(self.data.keys()):
                fid = open(prefix + '_Param-')


    def write_data(self,filename):
        """Writes final data to a file"""
        #import os
        print '~~~~~~~~ writing data from ' + self.filename + ' to ' + filename
        data = self.finaldata.filled(-999)
        dates = data[:,0]
        #convert dates to numpy array of integers
        datelist = []
        for dt in dates:
            datelist.append([dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second])
        dates = np.array(datelist)

        #get data
        data = data[:,1:data.shape[1]]

        fname = open(filename,'w')
        
        fname.write('## The following data have been collected by a Texas Water Development Board\n')
        fname.write('## instrument. These data are raw, uncorrected, and may contain\n')
        fname.write('## errors. The Board makes no warranties (including no warranties as to\n')
        fname.write('## merchantability or fitness) either expressed or implied with respect to\n')
        fname.write('## the data or its fitness for any specific application.\n')
        fname.write('##\n')
        fname.write('##\n')
        fname.write('## ASCII File generated from Instrument file: ' + self.filename + '\n')
        fname.write('## Plugin used to generate ASCII File: ' + self.__class__.__name__ + '\n')

        fname.write('## TWDB Site Name: ' + self.site + '\n')

        for line in self.header:
            fname.write(line)

        fname.write('## Timezone: ' + self.tz +'\n')

        fname.write('## NoData Value: -999.000000 \n')

        fname.write('## Next line contains column header information \n')
        header = '# Year, Month, Day, Hour, Minute, Second, ' + self.fieldheader
        fname.write(header + '\n')
        fname.write('## Next line contains data units information \n')
        header = '## Year, Month, Day, Hour, Minute, Second, ' + self.unitheader
        fname.write(header + '\n')

        for comment in self.extraheader:
            fname.write(comment)

        fname.close()

        np.savetxt('tmpdates.txt',dates,fmt='%i',delimiter=',')
        np.savetxt('tmpdata.txt',data,fmt='%08.5f',delimiter=',')
        os.popen('paste -d, tmpdates.txt tmpdata.txt >> ' + filename)
        os.popen('rm tmp*.txt')
    
