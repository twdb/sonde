from datetime import datetime
import glob
import re

from configobj import ConfigObj
from nose.tools import assert_almost_equal, eq_, set_trace
import numpy as np
import quantities as pq

from sonde import Sonde
from sonde import quantities as sq

def test_files():
    test_file_paths = [i for i in glob.glob('./*_test_files/*_test.txt')]

    for test_file_path in test_file_paths:
        tested_file_extension = test_file_path.split('_')[-2]
        tested_file_path = '.'.join([test_file_path.rsplit('_' + tested_file_extension, 1)[0],
                                     tested_file_extension])

        yield check_file, test_file_path, tested_file_path


def check_file(test_file_path, sonde_file_path):
    test_file = ConfigObj(test_file_path, unrepr=True)

    file_format = test_file['header']['format']
    sonde = Sonde(sonde_file_path, file_format=file_format)

    check_format_parameters(test_file['format_parameters'], sonde)

    parameters = test_file['data']['parameters']
    units = test_file['data']['units']

    for test_data in test_file['data']['test_data']:
        check_values_match(test_data, parameters, units, sonde)


def check_values_match(test_data, parameters, units, sonde):
    date_format = "%m/%d/%Y %H:%M:%S"

    date = datetime.strptime(test_data[0], date_format)
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
        assert_almost_equal(test_datum, sonde_datum)


def check_format_parameters(format_parameters, sonde):
    for parameter_name, test_value in format_parameters.items():
        if test_value == '':
            continue

        test_value = str(test_value)

        assert parameter_name in sonde.format_parameters, "format parameter '%s' not found in sonde.format_parameters" % parameter_name


        sonde_parameter = sonde.format_parameters[parameter_name]

        if re.match('\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', test_value):
            test_value = datetime.strptime(test_value, "%m/%d/%Y %H:%M:%S")


        assert test_value == sonde_parameter, "format parameter '%s' doesn't match: %s != %s" % (parameter_name, test_value, sonde_parameter)
