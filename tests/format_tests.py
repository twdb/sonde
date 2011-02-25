from datetime import datetime
import glob
import re

from configobj import ConfigObj
from nose.tools import assert_almost_equal, eq_, set_trace
import numpy as np
import quantities as pq

from sonde import Sonde
from sonde import quantities as sq
from sonde.timezones import cst, cdt


def test_files():
    test_file_paths = glob.glob('./*_test_files/*_test.txt')

    for test_file_path in test_file_paths:
        tested_file_extension = test_file_path.split('_')[-2]
        tested_file_path = '.'.join([test_file_path.rsplit('_' + tested_file_extension, 1)[0],
                                     tested_file_extension])

        yield check_file, test_file_path, tested_file_path


def check_file(test_file_path, sonde_file_path):
    global tz
    tz = None
    test_file = ConfigObj(test_file_path, unrepr=True)

    file_format = test_file['header']['format']


    # force cst, as the python naive datetime automatically converts
    # to cst which tends to screw things up
    if 'tz' in test_file['format_parameters'] and test_file['format_parameters']['tz'].lower() == 'cdt':
        tz = cdt
    else:
        tz = cst

    sonde = Sonde(sonde_file_path, file_format=file_format, tzinfo=tz)

    check_format_parameters(test_file['format_parameters'], sonde)

    parameters = test_file['data']['parameters']
    units = test_file['data']['units']

    for test_data in test_file['data']['test_data']:
        check_values_match(test_data, parameters, units, sonde)


def check_values_match(test_data, parameters, units, sonde):
    date = _convert_to_aware_datetime(test_data[0])

    assert date in sonde.dates, "date not found in sonde: %s" % (date)

    for parameter, unit, test_value in zip(parameters, units, test_data[1:]):
        sonde_datum = sonde.data[parameter][sonde.dates == date]

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


def check_format_parameters(format_parameters, sonde):
    for parameter_name, test_value in format_parameters.items():
        if test_value == '':
            continue

        assert parameter_name in sonde.format_parameters, "format parameter '%s' not found in sonde.format_parameters" % parameter_name

        sonde_parameter = sonde.format_parameters[parameter_name]

        # if we are testing a datetime value
        if re.match('\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', test_value):
            test_value = _convert_to_aware_datetime(test_value)

        assert test_value == sonde_parameter, "format parameter '%s' doesn't match: %s != %s" % (parameter_name, test_value, sonde_parameter)


def _tz_offset_string(tzinfo):
    """
    Return a tzoffset string in the form +HHMM or -HHMM as required
    for parsing the '%z' directive of the the datetime strptime()
    method's format for parsing datetime strings
    """
    offset = tzinfo.utcoffset(tzinfo)

    hours = offset.days * 24 + offset.seconds/3600
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
