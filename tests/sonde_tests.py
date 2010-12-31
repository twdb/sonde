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
from nose.tools import assert_almost_equal, set_trace
import numpy as np
import quantities as pq
import re
import sys


# Add path to sonde to sys.path for development
#sonde_path = os.path.join(os.path.dirname(__file__), '..')
#sys.path.append(os.path.join(sonde_path))


from sonde import BaseSondeDataset, Sonde
from sonde import quantities as sq
from sonde.timezones import cdt, cst
from sonde.formats import ysi


ysi_test_files_path = os.path.join(os.path.dirname(__file__), 'ysi_test_files')


class SondeTestDataset(BaseSondeDataset):
    """
    A test dataset
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
            'BAT01': np.array([ 6.2,  6.2,  6.2, 5.6,  5.6,  5.6]) * pq.volt,
            'CON02': np.array([-0.   , -0.   ,  8.326,  0.782,  1.964,  0.174]) * sq.mScm,
            'DOX02': np.array([  95.8  ,  101.767,   82.465, 102.95 ,  102.094,  109.647]) * pq.percent,
            'TEM01': np.array([ 23.45,  25.24,  21.34, 25.7 ,  26.  ,  20.38]) * pq.degC,
            'WSE01': np.array([ 1, 1, 1, 1, 1, 1]) * pq.m,
            }

        self.parameters = {
            'TEM01' : ('Water Temperature', pq.degC),
            'CON02' : ('Conductivity(Not Normalized)', sq.mScm),
            'WSE01' : ('Water Surface Elevation (No Atm Pressure Correction)', pq.m),
            'BAT01' : ('Battery Voltage', pq.volt),
            'DOX02' : ('Dissolved Oxygen Saturation Concentration', pq.percent),
            }


                 
class BaseSondeDataset_Test():
    def setUp(self):
        self.test_dataset = SondeTestDataset()

    def test_set_and_get_standard_unit(self):
        self.test_dataset.set_standard_unit('WSE01', pq.ft)
        assert pq.ft == self.test_dataset.get_standard_unit('WSE01')



if __name__ == '__main__':
    nose.run()
