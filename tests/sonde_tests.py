# -*- coding: utf-8 -*-
"""
    Sonde Tests
    ~~~~~~~~~~~

    These tests are run to make sure Sonde is working properly
"""
from __future__ import with_statement

import collections
import csv
from datetime import datetime
import os
import nose
from nose.tools import assert_almost_equal, eq_, set_trace
import numpy as np
import quantities as pq

from sonde import BaseSondeDataset, Sonde
from sonde import quantities as sq
from sonde.timezones import cdt, cst
from sonde.formats import ysi

ysi_test_files_path = os.path.join(os.path.dirname(__file__), 'ysi_test_files')



class SondeTestDataset(BaseSondeDataset):
    """
    A dummy test dataset - so aspects of BaseSondeDataset can be
    tested independent of parsing logic
    """
    def __init__(self):
        super(SondeTestDataset, self).__init__()

    def _read_data(self):
        date_str_list = ['2010-12-23 11:00:24',
                         '2010-12-23 12:00:24',
                         '2010-12-23 13:00:24',
                         '2010-12-23 14:00:24',
                         '2010-12-23 15:00:24',
                         '2010-12-23 16:00:24',]

        date_fmt = '%Y-%m-%d %H:%M:%S'

        date_list = []
        for date_str in date_str_list:
            date = datetime.strptime(date_str, date_fmt)
            date = date.replace(tzinfo=cdt)
            date_list.append(date)

        self.dates = np.array(date_list)

        self.data = {
            'instrument_battery_voltage': np.array([ 6.2,  6.2,  6.2, 5.6,  5.6,  5.6]) * pq.volt,
            'water_electrical_conductivity': np.array([-0.   , -0.   ,  8.326,  0.782,  1.964,  0.174]) * sq.mScm,
            'water_dissolved_oxygen_percent_saturation': np.array([  95.8  ,  101.767,   82.465, 102.95 ,  102.094,  109.647]) * pq.percent,
            'water_temperature': np.array([ 23.45,  25.24,  21.34, 25.7 ,  26.  ,  20.38]) * pq.degC,
            'water_depth_non_vented': np.array([ 1, 1, 1, 1, 1, 1]) * pq.m,
            }

        self.parameters = {
            'water_temperature' : ('Water Temperature', pq.degC),
            'water_electrical_conductivity' : ('Conductivity(Not Normalized)', sq.mScm),
            'water_depth_non_vented' : ('Water Surface Elevation (No Atm Pressure Correction)', pq.m),
            'instrument_battery_voltage' : ('Battery Voltage', pq.volt),
            'water_dissolved_oxygen_percent_saturation' : ('Dissolved Oxygen Saturation Concentration', pq.percent),
            }


                 
class BaseSondeDataset_Test():
    def setup(self):
        self.dataset = SondeTestDataset()

        self.fahrenheit_temps = [23,
                                 55,
                                 3994,
                                 -99.67,
                                 0,
                                 32,
                                 ]

        self.celsius_temps = [-5,
                              12.77777777778,
                              2201.11111111111,
                              -73.15,
                              -17.7777777778,
                              0,
                              ]

        self.kelvin_temps = [268.15,
                             285.92777777778,
                             2474.261111111111,
                             200,
                             255.37222222222,
                             273.15,
                             ]



    def test_set_and_get_standard_unit(self):
        self.dataset.set_standard_unit('water_depth_non_vented', pq.ft)

        # make sure the standard unit has been set
        assert pq.ft == self.dataset.get_standard_unit('water_depth_non_vented')

        # make sure unit conversion happened
        for value in self.dataset.data["water_depth_non_vented"]:
            assert_almost_equal(value.magnitude,
                                3.280839895013123)


    def test_rescale_parameter_elevation(self):
        self.dataset.data['water_depth_non_vented'] = np.ones(6) * 3.280839895013123 * pq.ft
        self.dataset.rescale_parameter('water_depth_non_vented')

        for value in self.dataset.data["water_depth_non_vented"]:
            eq_(value.units, pq.m)
            assert_almost_equal(value.magnitude,
                                1)


    def test_rescale_parameter_temperature_celsius_to_fahrenheit(self):
        self.dataset.set_standard_unit('water_temperature', pq.degF)

        self.dataset.data['water_temperature'] = np.array(self.celsius_temps) * pq.degC
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.fahrenheit_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    def test_rescale_parameter_temperature_celsius_to_kelvin(self):
        self.dataset.set_standard_unit('water_temperature', pq.degK)

        self.dataset.data['water_temperature'] = np.array(self.celsius_temps) * pq.degC
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.kelvin_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    def test_rescale_parameter_temperature_celsius_to_celsius(self):
        self.dataset.set_standard_unit('water_temperature', pq.degC)

        self.dataset.data['water_temperature'] = np.array(self.celsius_temps) * pq.degC
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.celsius_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    def test_rescale_parameter_temperature_fahrenheit_to_celsius(self):
        self.dataset.set_standard_unit('water_temperature', pq.degC)

        self.dataset.data['water_temperature'] = np.array(self.fahrenheit_temps) * pq.degF
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.celsius_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    def test_rescale_parameter_temperature_fahrenheit_to_kelvin(self):
        self.dataset.set_standard_unit('water_temperature', pq.degK)

        self.dataset.data['water_temperature'] = np.array(self.fahrenheit_temps) * pq.degF
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.kelvin_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    def test_rescale_parameter_temperature_kelvin_to_celsius(self):
        self.dataset.set_standard_unit('water_temperature', pq.degC)

        self.dataset.data['water_temperature'] = np.array(self.kelvin_temps) * pq.degK
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.celsius_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    def test_rescale_parameter_temperature_kelvin_to_fahrenheit(self):
        self.dataset.set_standard_unit('water_temperature', pq.degF)

        self.dataset.data['water_temperature'] = np.array(self.kelvin_temps) * pq.degK
        self.dataset.rescale_parameter('water_temperature')

        for converted, expected in zip(self.dataset.data["water_temperature"],
                                       self.fahrenheit_temps):
            assert_almost_equal(converted.magnitude,
                                expected)


    
if __name__ == '__main__':
    nose.run()
