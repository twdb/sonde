"""
    sonde.Sonde
    ~~~~~~~~~~~

    This module implements the main Sonde object.

"""
from __future__ import absolute_import

import datetime
import os
import traceback
import warnings

import numpy as np
import quantities as pq
import pytz
import seawater

from sonde import quantities as sq
from sonde import util
from sonde.timezones import UTCStaticOffset


#XXX: put this into a proper config file
#: The default timezone to use when reading files
#default_timezone = cst #i.e utc-6
default_utc_static_offset = -6
default_static_timezone = UTCStaticOffset(default_utc_static_offset)
default_timezone = pytz.timezone('US/Central')

#: A dict that contains all the parameters that could potentially be
#: read from a data file, along with their standard units. This list
#: is exhaustive and will be fully populated whether or not data is or
#: even available in a particular format. See the `parameters`
#: attribute for parameters that are available for a particular file.
#: where possible we follow netcdf CF standard for parameter name and unit
#: (http://cf-pcmdi.llnl.gov/) in other cases we follow the general CF naming
#: guidelines
master_parameter_list = {
    'air_pressure': ('Atmospheric Pressure', pq.pascal),
    'air_temperature': ('Air Temperature', pq.degC),
    'eastward_water_velocity': ('Eastward Water Velocity', sq.mps),
    'instrument_battery_voltage': ('Battery Voltage', pq.volt),
    'northward_water_velocity': ('Northward Water Velocity', sq.mps),
    'seawater_salinity': ('Salinity', sq.psu),
    'water_depth_non_vented': (
        'Depth is the vertical distance below the water surface. '
        '(No Atm Pressure Correction)', sq.mH2O),
    'water_depth_vented': (
        'Depth is the vertical distance below the water surface. '
        '(w/ Atm Pressure Correction)', sq.mH2O),
    'water_dissolved_oxygen_concentration': (
        'Dissolved Oxygen Concentration', sq.mgl),
    'water_dissolved_oxygen_percent_saturation': (
        'Dissolved Oxygen Saturation Concentration', pq.percent),
    'water_electrical_conductivity': (
        'Electrical Conductivity(Not Normalized)', sq.mScm),
    'water_ph': ('pH Level', pq.dimensionless),
    'water_pressure': ('Water Pressure', pq.psi),
    'water_specific_conductance': ('Specific Conductance(Normalized @25degC)',
                                   sq.mScm),
    'water_surface_elevation': ('Water Surface Elevation', pq.m),
    'water_temperature': ('Water Temperature', pq.degC),
    'water_total_dissolved_salts': ('Total Dissolved Salts', sq.mgl),
    'water_turbidity': ('Turbidity', sq.ntu),
    'upward_water_velocity': ('Upward Water Velocity', sq.mps),
    'water_x_velocity': ('Water Velocity in x direction', sq.mps),
    'water_y_velocity': ('Water in y direction', sq.mps),
    'chlorophyll_a': ('Chlorophyll-a', pq.ugl),
    'Phycoerythrin': ('Phycoerythrin Red Green Algae', pq.cellsml),
    'Phycocyanin': ('Phycocyanin Blue Green Algae', pq.cellsml),
    }


def open_sonde(data_file, file_format=None, *args, **kwargs):
    """
    Wrapper for Sonde(), just here to make a nicer API
    """
    return Sonde(data_file, file_format=file_format, *args, **kwargs)


def Sonde(data_file, file_format=None, *args, **kwargs):
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

        if file_format == False:
            raise Exception("File Format Autodetection Failed. Try "
                            "specifying the file_format.")

    if 'ysi' in file_format.lower():
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

    if file_format.lower() == 'generic':
        from sonde.formats.generic import GenericDataset
        return GenericDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'midgewater':
        from sonde.formats.midgewater import MidgewaterDataset
        return MidgewaterDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'espey':
        from sonde.formats.espey import EspeyDataset
        return EspeyDataset(data_file, *args, **kwargs)

    if file_format.lower() == 'lcra':
        from sonde.formats.lcra import LcraDataset
        return LcraDataset(data_file, *args, **kwargs)
    else:
        raise NotImplementedError("file format '%s' is not supported" % \
                                   (file_format,))


def autodetect(data_file, filename=None):
    """
    returns file_format string if successfully able to detect file
    format, returns False otherwise.

    data_file can be either a filename string or a file-like object.
    If it is a file-like object you can pass a file_name string if the
    file-like object doesn't have a name or filename attribute
    containing the filename.
    """

    if not filename:
        if type(data_file) == str:
            filename = data_file
        elif hasattr(data_file, 'name'):
            filename = data_file.name
        elif hasattr(data_file, 'filename'):
            filename = data_file.filename

    file_ext = filename.split('.')[-1].lower()

    if file_ext and file_ext == 'xls':
        temp_csv_path, xls_read_mode = util.xls_to_csv(data_file)
        fid = open(temp_csv_path, 'rb')
        lines = [fid.readline() for i in range(3)]
        fid.close()
        os.remove(temp_csv_path)

    else:
        if type(data_file) == str:
            fid = open(data_file, 'r')
        else:
            fid = data_file

        file_initial_location = fid.tell()
        fid.seek(0)
        lines = [fid.readline() for i in range(3)]
        fid.seek(file_initial_location)


    if lines[0].lower().find('greenspan') != -1:
        return 'greenspan'
    if lines[0].lower().find('macroctd') != -1:
        return 'macroctd'
    if lines[0].lower().find('minisonde4a') != -1:
        return 'hydrotech'
    if lines[0].lower().find('data file for datalogger.') != -1:
        return 'solinst'
    if lines[0].find('Serial_number:')!= -1 and lines[2].find('Project ID:')!= -1:
        return 'solinst'
    if lines[0].lower().find('log file name') != -1:
        return 'hydrolab'
    if lines[0].lower().find('pysonde csv format') != -1:
        return 'generic'
        # possible binary junk in first line of hydrotech file
    if lines[1].lower().find('log file name') != -1:
        return 'hydrotech'
    if lines[0].lower().find('the following data have been') != -1:
        return 'lcra'

    # ascii files for ysi in brazos riv.
    if lines[0].find('espey') != -1:
        return 'espey'

    #check for ysi:
    # binary
    if lines[0][0] == 'A':
        return 'ysi_binary'
    # txt file
    if lines[0].find('=') != -1:
        return 'ysi_text'
    if lines[0].find('##YSI ASCII Datafile=') != -1:
        return 'ysi_ascii'
    # cdf file
    if file_ext and file_ext == 'cdf':
        return 'ysi_cdf'
    if lines[0].find("Date") > -1 and lines[1].find("M/D/Y") > -1:
        return 'ysi_csv'

    #eureka try and detect degree symbol
    if lines[1].find('\xb0') > -1 or lines[2].find('Manta') > -1 or \
           lines[0].find('Start time : ') > -1:
        return 'eureka'

    # files from various intruments processed by an old script.
    if lines[0].lower().find('request date') != -1:
        return 'midgewater'
    else:
        return False


def find_tz(dt):
    """
    give a naive datetime.datetime object finds local timezone i.e
    includes dst effects
    """
    utc_offset = default_utc_static_offset + \
                 int(default_timezone.dst(dt).seconds / 3600)
    return UTCStaticOffset(utc_offset)


def merge(file_list, tz_list=None):
    """
    Merges all files in file_list
    tz_list specifies timezone of each file.
    options cst=utc-6, cdt=utc-5, auto=determine based on dataset.setup_time
    If tz_list == None then cst is assumed i.e UTC-6
       tz_list == auto then cst/cdt is determined from dataset.setup_date
       tz_list == ['utc-6','utc-5', etc]
    returns a Sonde object
    """
    from sonde.formats.merge import MergeDataset

    if tz_list is None:
        tz_list = [default_static_timezone for fn in file_list]
    elif tz_list == 'auto':
        tz_list = ['auto' for fn in file_list]
    #else:
    #     tz_list = [UTCStaticOffset(int(tz.lower().strip('utc')))
    #                for tz in tz_list]

    metadata = dict()
    data = dict()

    metadata['dates'] = np.empty(0, dtype=datetime.datetime)
    metadata['data_file_name'] = np.empty(0, dtype='|S100')
    metadata['instrument_serial_number'] = np.empty(0, dtype='|S15')
    metadata['instrument_manufacturer'] = np.empty(0, dtype='|S15')

    for param, unit in master_parameter_list.items():
        data[param] = np.empty(0, dtype='<f8') * unit[-1]

    for file_name, tz in zip(file_list, tz_list):
        try:
            if tz == 'auto':
                tmp = Sonde(file_name)
                # tz = UTCStaticOffset(utc_offset)
                tz = find_tz(tmp.setup_time)
            elif isinstance(tz, str):
                tz = UTCStaticOffset(int(tz.lower().strip('utc')))
            dataset = Sonde(file_name, tzinfo=tz)
        except:
            warnings.warn('merged failed for file %s with error: %s' % (file_name, traceback.print_exc()), Warning)
            continue

        fn_list = np.zeros(len(dataset.dates), dtype='|S100')
        sn_list = np.zeros(len(dataset.dates), dtype='|S15')
        m_list = np.zeros(len(dataset.dates), dtype='|S15')

        fn_list[:] = os.path.split(file_name)[-1]
        sn_list[:] = dataset.serial_number
        m_list[:] = dataset.manufacturer

        metadata['dates'] = np.hstack((metadata['dates'], dataset.dates))
        metadata['data_file_name'] = np.hstack(
            (metadata['data_file_name'], fn_list))
        metadata['instrument_serial_number'] = np.hstack(
            (metadata['instrument_serial_number'], sn_list))
        metadata['instrument_manufacturer'] = np.hstack(
            (metadata['instrument_manufacturer'], m_list))

        no_data = np.zeros(len(dataset.dates))
        no_data[:] = np.nan
        for param in master_parameter_list.keys():
            if param in dataset.data.keys():
                tmp_data = dataset.data[param]
            else:
                tmp_data = no_data

            data[param] = np.hstack((data[param], tmp_data))
        print 'merged: %s' % file_name

    for param, unit in master_parameter_list.items():
        if np.all(np.isnan(data[param])):
            del data[param]
        else:
            data[param] = data[param] * unit[-1]

    return MergeDataset(metadata, data)


class BaseSondeDataset(object):
    """
    The base class that all sonde format objects should inherit. This
    class contains all the attributes and methods that are common to
    all data formats; it is not intended to be instantiated directly.
    """
    #: A dict that maps parameter codes to long descriptions and their
    #: standard units
    parameters = {}

    def __init__(self, data_file=None):
        if type(data_file) == str:
            self.file_name = data_file
        elif type(data_file) == file:
            self.file_name = data_file.name
        self.data = {}
        self.dates = []
        self.format_parameters = {}
        self.manufacturer = ''
        self.serial_number = ''
        self._read_data()
        self.rescale_all()

        if 'water_specific_conductance' in self.data or \
               'water_electrical_conductivity' in self.data:
            self._calculate_salinity()

        #if 'site_name' in self.format_parameters.keys():
        #    site_name = self.format_parameters['site_name']
        #    @todo tz check

        if default_static_timezone and self.dates[0].tzinfo != None:
            self.convert_timezones(default_static_timezone)

        if not hasattr(self, 'setup_time'):
            self.setup_time = self.dates[0]

        if not hasattr(self, 'start_time'):
            self.start_time = self.dates[0]

        if not hasattr(self, 'stop_time'):
            self.stop_time = self.dates[-1]

        if not hasattr(self, 'serial_number'):
            self.serial_number = ''

        if not hasattr(self, 'site_name'):
            self.site_name = ''

    def apply_mask(self, mask, parameters=None):
        """
        remove data and headers where mask=False
        if parameters = None remove all data
        else apply to list of parameters by setting
        parameter values to np.nan based on mask
        """
        if parameters is None:
            self.dates = self.dates[mask]
            for key in self.data.keys():
                self.data[key] = self.data[key][mask]

            self.manufacturer = self.manufacturer[mask]
            self.data_file = self.data_file[mask]
            self.serial_number = self.serial_number[mask]
        else:
            for parameter in parameters:
                self.data[parameter][~mask] = np.nan

    def write(self, file_name, file_format='netcdf4', fill_value='-999.99',
              metadata={}, disclaimer='', float_fmt='%5.2f'):
        """
        fill_value must be a float
        """
        data = self.data.copy()
        #convert to column file_format
        if isinstance(self.data_file, str):
            fn_list = np.zeros(len(self.dates), dtype='|S100')
            fn_list[:] = self.data_file
        else:
            fn_list = self.data_file

        if isinstance(self.serial_number, str):
            sn_list = np.zeros(len(self.dates), dtype='|S100')
            sn_list[:] = self.serial_number
        else:
            sn_list = self.serial_number

        if isinstance(self.manufacturer, str):
            m_list = np.zeros(len(self.dates), dtype='|S100')
            m_list[:] = self.manufacturer
        else:
            m_list = self.manufacturer

        metadata['original_data_file'] = fn_list
        metadata['instrument_serial_number'] = sn_list
        metadata['instrument_manufacturer'] = m_list
        metadata['fill_value'] = fill_value

        if file_format.lower() == 'netcdf4':
            self._write_netcdf4(file_name, metadata, self.dates, data,
                                disclaimer)
        elif file_format.lower() == 'csv':
            self._write_csv(file_name, metadata, self.dates, data,
                            disclaimer, float_fmt)
        else:
            warnings.warn('Unknown output file_format: %s' % file_format,
                          Warning)
            raise

    def _write_csv(self, file_name, metadata, dates, data, disclaimer,
                   float_fmt):
        """
        write output in csv format
        """

        version = '# file_format: pysonde csv format version 1.0\n'
        header = [version]
        #prepend parameter list and units with single #
        param_header = '# datetime, '
        unit_header = '# yyyy/mm/dd HH:MM:SS, '
        dtype_fmts = ['|S19']
        fmt = '%s, '
        for param in np.sort(data.keys()):
            param_header += param + ', '
            try:
                unit_header += data[param].dimensionality.keys()[0].symbol + \
                               ', '
            except:
                unit_header += 'nd, '
            fill_value = float(metadata['fill_value']) * data[param].units
            data[param][np.isnan(data[param])] = fill_value
            dtype_fmts.append('f8')
            fmt += float_fmt + ', '

        #prepend disclaimer and metadata with ##
        for line in disclaimer.splitlines():
            header.append('# disclaimer: ' + line + '\n')

        #for key,val in metadata.items():
        #    if not isinstance(val, np.ndarray):
        #        header.append('# ' + str(key) + ': ' + str(val) + '\n')
        #    else:
        #        param_header += key + ', '
        #        unit_header += 'n/a, '
        #        dtype_fmts.append(val.dtype)
        #        fmt += '%s, '
        for key in np.sort(metadata.keys()):
            if not isinstance(metadata[key], np.ndarray):
                header.append('# %s: %s\n' % (str(key), str(metadata[key])))

            else:
                param_header += key + ', '
                unit_header += 'n/a, '
                dtype_fmts.append(metadata[key].dtype)
                fmt += '%s, '

        #remove trailing commas
        param_header = param_header[:-2] + '\n'
        unit_header = unit_header[:-2] + '\n'
        fmt = fmt[:-2]

        header.append('# timezone: ' + str(self.default_tzinfo) + '\n')
        header.append(param_header)
        header.append(unit_header)

        dtype = np.dtype({
            'names': param_header.replace(' ', '').strip('#\n').split(','),
            'formats': dtype_fmts})

        write_data = np.zeros(dates.size, dtype=dtype)
        write_data['datetime'] = np.array(
            [datetime.datetime.strftime(dt, '%Y/%m/%d %H:%M:%S')
             for dt in dates])

        for key, val in metadata.items():
            if isinstance(val, np.ndarray):
                write_data[key] = val

        for param in data.keys():
            write_data[param] = data[param]

        #start writing file
        fid = open(file_name, 'w')
        fid.writelines(header)
        np.savetxt(fid, write_data, fmt=fmt)
        fid.close()

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
                self.data[param_code] += self._temperature_offset(
                    current_unit, std_unit)

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
            return -1 * (32 * (5.0 / 9)) * pq.degC

        elif from_symbol == 'degF' and to_symbol == 'K':
            return 459.67 * (5.0 / 9) * pq.degK

        elif from_symbol == 'K' and to_symbol == 'degC':
            return -273.15 * pq.degC

        elif from_symbol == 'K' and to_symbol == 'degF':
            return -459.67 * pq.degF

        else:
            raise NotImplementedError(
                "conversion from %s to %s not supported" %
                (from_symbol, to_symbol))

    def _calculate_salinity(self):
        """
        Calculate salinity if salinity parameter is missing but
        conductivity is present.
        """
        params = self.parameters.keys()
        if 'seawater_salinity' in params:
            return
        else:
            if 'water_specific_conductance' in params:
                T = 25.0
                cond = self.data['water_specific_conductance'].rescale(
                    sq.mScm).magnitude
            elif 'water_electrical_conductivity' in params:
                current_unit = self.data['water_temperature'].units
                temp_celsius = self.data['water_temperature'].rescale(pq.degC)
                temp_celsius += self._temperature_offset(current_unit, pq.degC)
                T = temp_celsius.magnitude
                cond = self.data['water_electrical_conductivity'].rescale(
                    sq.mScm).magnitude
            else:
                return

            if 'water_depth_non_vented' in params:
                P = self.data['water_depth_non_vented'].rescale(
                    sq.dbar).magnitude + (pq.atm).rescale(sq.dbar).magnitude
            elif 'water_depth_vented' in params:
                P = self.data['water_depth_vented'].rescale(sq.dbar).magnitude
            else:
                P = (pq.atm).rescale(sq.dbar).magnitude

            R = cond / 42.914
            sal = seawater.salt(R, T, P)

            self.set_standard_unit('seawater_salinity', sq.psu)
            self.data['seawater_salinity'] = sal * sq.psu

    def convert_timezones(self, to_tzinfo):
        """
        Convert all dates to some timezone. The argument `to_tzinfo`
        must be an instance of datetime.tzinfo, either from the
        datetime library itself or the pytz library.
        """

        # If to_tzinfo is a pytz timezone, then use the normalize
        # method so pytz can do normalize DST transition data
        if isinstance(to_tzinfo, pytz.tzinfo.BaseTzInfo):
            self.dates = np.array(
                [to_tzinfo.normalize(date.astimezone(to_tzinfo))
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
        return [np.array([]), np.array([])]
