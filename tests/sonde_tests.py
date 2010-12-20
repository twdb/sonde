# -*- coding: utf-8 -*-
"""
    Sonde Tests
    ~~~~~~~~~~~

    These tests are run to make sure Sonde is working properly.


"""
from __future__ import with_statement

import collections
import csv
from datetime import datetime
import os
from nose.tools import assert_almost_equal, set_trace
import numpy as np
import re
import sys
import unittest


# Add path to sonde to sys.path for development
#sonde_path = os.path.join(os.path.dirname(__file__), '..')
#sys.path.append(os.path.join(sonde_path))

from ..sonde.timezones import cdt, cst
from ..sonde.formats import ysi


ysi_test_files_path = os.path.join(os.path.dirname(__file__), 'ysi_test_files')


def ysi_csv_read(filename):
    ysi_csv = collections.namedtuple('ysi_csv', 'dates, temps, spconds, depths, odos')

    with open(filename, 'rb') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        # loop through first two header lines
        for i in range(2):
            csv_file.next()

        date_list = []
        temp_list = []
        spcond_list = []
        depth_list = []
        odo_list = []

        for row in csv_reader:
            timestamp = row[0] + ' ' + row[1]
            date = datetime.strptime(timestamp, '%m/%d/%y %H:%M:%S')
            date = date.replace(tzinfo=cdt)
            date_list.append(date)
            temp_list.append(row[2])
            spcond_list.append(row[3])
            depth_list.append(row[4])
            odo_list.append(row[5])

        ysi_csv.dates = np.array(date_list)
        ysi_csv.temps = np.array(temp_list)
        ysi_csv.spconds = np.array(spcond_list)
        ysi_csv.depths = np.array(depth_list)
        ysi_csv.odos = np.array(odo_list)

    return ysi_csv


def compare_quantity_and_csv_str(quantities, str_list):
    for quantity, string in zip(quantities, str_list):
        assert_almost_equal(quantity.base, float(string))


class YSIReaderTestCase(unittest.TestCase):
    def setUp(self):
        csv_test_file_path = ysi_test_files_path + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = ysi_test_files_path + '/BAYT_20070323_CDT_YS1772AA_000.dat'
        ysi_param_file_path = ysi_test_files_path + '/ysi_param.def'

        self.ysi_reader = ysi.YSIReader(ysi_test_file_path, param_file=ysi_param_file_path, tzinfo=cdt)
        self.ysi_csv = ysi_csv_read(csv_test_file_path)

    def test_ysi_reader_dates_match_csv(self):
        for date_pair in zip(self.ysi_reader.dates, self.ysi_csv.dates):
            assert date_pair[0] == date_pair[1], "%r != %r" % (str(date_pair[0]),  str(date_pair[1]))


class YSIDatasetTestCase(unittest.TestCase):
    def setUp(self):
        csv_test_file_path = ysi_test_files_path + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = ysi_test_files_path + '/BAYT_20070323_CDT_YS1772AA_000.dat'
        ysi_param_file_path = ysi_test_files_path + '/ysi_param.def'

        self.ysi_dataset = ysi.Dataset(ysi_test_file_path, param_file=ysi_param_file_path, tzinfo=cdt)
        self.ysi_csv = ysi_csv_read(csv_test_file_path)

    def test_ysi_dataset_dates_match_csv(self):
        for date_pair in zip(self.ysi_dataset.dates, self.ysi_csv.dates):
            assert date_pair[0] == date_pair[1], "%r != %r" % (str(date_pair[0]), str(date_pair[1]))

    def test_ysi_dataset_temps_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['TEM01'], self.ysi_csv.temps)

    def test_ysi_dataset_spconds_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['CON01'], self.ysi_csv.spconds)

    def test_ysi_dataset_depths_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['WSE01'], self.ysi_csv.depths)

    def test_ysi_dataset_odos_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['DOX02'], self.ysi_csv.odos)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(YSIReaderTestCase))
    suite.addTest(unittest.makeSuite(YSIDatasetTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
