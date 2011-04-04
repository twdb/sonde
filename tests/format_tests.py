from datetime import datetime
import glob
import re

from configobj import ConfigObj
from nose.tools import assert_almost_equal, eq_, set_trace
import numpy as np
import quantities as pq

import sonde
from sonde import quantities as sq
from sonde.timezones import cst, cdt

# global tz
tz = None


def test_files():
    test_config_paths = glob.glob('./*_test_files/*_test.txt')

    for test_config_path in test_config_paths:
        sonde_file_extension = test_config_path.split('_')[-2]
        sonde_file_base = test_config_path.rsplit('_' + sonde_file_extension,
                                                  1)[0]
        sonde_file_path = '.'.join([sonde_file_base,
                                    sonde_file_extension])

        test_file_config = ConfigObj(open(test_config_path), unrepr=True)

        yield check_autodetect, test_file_config, sonde_file_path

        yield check_file, test_file_config, sonde_file_path

        with open(sonde_file_path) as sonde_file_fid:
            yield check_file, test_file_config, sonde_file_fid


def check_autodetect(test_file, sonde_file):
    file_format = test_file['header']['format']
    autodetect_result = sonde.autodetect(sonde_file)

    assert autodetect_result == file_format, \
           "Autodetection failed: %s != %s" % (autodetect_result, file_format)


def check_file(test_file, sonde_file):
    global tz

    file_format = test_file['header']['format']

    # force cst, as the python naive datetime automatically converts
    # to cst which tends to screw things up
    if 'tz' in test_file['format_parameters'] and \
           test_file['format_parameters']['tz'].lower() == 'cdt':
        tz = cdt
    else:
        tz = cst

    sonde_file = sonde.open_sonde(sonde_file, file_format=file_format,
                                  tzinfo=tz)
    check_format_parameters(test_file['format_parameters'], sonde_file)

    parameters = test_file['data']['parameters']
    units = test_file['data']['units']

    for test_data in test_file['data']['test_data']:
        check_values_match(test_data, parameters, units, sonde_file)


def check_values_match(test_data, parameters, units, sonde_file):
    date = _convert_to_aware_datetime(test_data[0])

    assert date in sonde_file.dates, \
           "date not found in sonde_file: %s" % (date)

    for parameter, unit, test_value in zip(parameters, units, test_data[1:]):
        sonde_datum = sonde_file.data[parameter][sonde_file.dates == date]

        if unit in pq.__dict__:
            test_quantity = pq.__dict__[unit]
        elif unit in sq.__dict__:
            test_quantity = sq.__dict__[unit]
        else:
            raise "config error: could not find quantity for '%s '" % unit

        if test_value == 'nan':
            assert np.isnan(sonde_datum)
            continue

        test_datum = (test_value * test_quantity).rescale(sonde_datum.units)

        # if value in the test file is less precise than the actual
        # data value, then just check the number of decimal places of
        # the test value. Note: this means trailing zeros ignored
        if len(str(test_value).split('.')) == 2:
            places = len(str(test_value).split('.')[1])
            assert_almost_equal(test_datum, sonde_datum, places)
        else:
            assert_almost_equal(test_datum, sonde_datum)


def check_format_parameters(format_parameters, sonde_file):
    for parameter_name, test_value in format_parameters.items():
        if test_value == '':
            continue

        # parameters on the sonde_file object itself; historically, these
        # used to be in the format_parameters dict but now they are on
        # the sonde_file object and it's not worth the effort to rearrange
        # all the test files
        sonde_parameters = ['serial_number', 'site_name', 'setup_time',
                            'start_time', 'stop_time']

        if parameter_name in sonde_parameters:
            assert hasattr(sonde_file, parameter_name), \
                   "format parameter '%s' not found in " \
                   "sonde_file.format_parameters" % parameter_name
            sonde_parameter = getattr(sonde_file, parameter_name)

        else:
            assert parameter_name in sonde_file.format_parameters, \
                   "format parameter '%s' not found in " \
                   "sonde_file.format_parameters" % parameter_name
            sonde_parameter = sonde_file.format_parameters[parameter_name]

        # if we are testing a datetime value
        if re.match('\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', test_value):
            test_value = _convert_to_aware_datetime(test_value)

        assert test_value == sonde_parameter, \
               "format parameter '%s' doesn't match: '%s' != '%s'" % \
               (parameter_name, test_value, sonde_parameter)


def _tz_offset_string(tzinfo):
    """
    Return a tzoffset string in the form +HHMM or -HHMM as required
    for parsing the '%z' directive of the the datetime strptime()
    method's format for parsing datetime strings
    """
    offset = tzinfo.utcoffset(tzinfo)

    hours = offset.days * 24 + offset.seconds / 3600
    minutes = (offset.seconds % 3600) / 60

    return "%+03d%02d" % (hours, minutes)


def _convert_to_aware_datetime(datetime_string):
    """
    Convert to a datetime string to a datetime object, taking tz into
    account if it is set
    """
    date_format = "%m/%d/%Y %H:%M:%S"
    dt = datetime.strptime(datetime_string, date_format)

    if tz:
        dt = dt.replace(tzinfo=tz)

    return dt
