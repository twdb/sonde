# -*- coding: utf-8 -*-
"""
    YSI Format Tests
    ~~~~~~~~~~~~~~~~

    These tests make sure that the YSI format module is working
    correctly
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

from sonde import Sonde
from sonde import quantities as sq
from sonde.timezones import cdt, cst
from sonde.formats import ysi


YSI_TEST_FILES_PATH = os.path.join(os.path.dirname(__file__), 'ysi_test_files')


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





#-------------------------------------------------------------------
# Tests for ysi.YSIReader
#-------------------------------------------------------------------
class YSIReaderTestBase():
    def test_ysi_dates_match_csv(self):
        for date_pair in zip(self.ysi_reader.dates, self.ysi_csv.dates):
            assert date_pair[0] == date_pair[1], "%r != %r" % (str(date_pair[0]), str(date_pair[1]))


class YSIReader_Test(YSIReaderTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'

        self.ysi_reader = ysi.YSIReader(ysi_test_file_path, tzinfo=cdt)
        self.ysi_csv = ysi_csv_read(csv_test_file_path)


class YSIReaderExplicitParamDef_Test(YSIReaderTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'
        ysi_param_file_path = YSI_TEST_FILES_PATH + '/ysi_param.def'

        self.ysi_reader = ysi.YSIReader(ysi_test_file_path, param_file=ysi_param_file_path, tzinfo=cdt)
        self.ysi_csv = ysi_csv_read(csv_test_file_path)


def YSIReaderNaiveDatetime_Test():
    """
    Test that naive datetimes are allowed
    """
    ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'
    
    ysi_reader = ysi.YSIReader(ysi_test_file_path)
    assert ysi_reader.dates != []

#-------------------------------------------------------------------


class YSICompareWithCSVTestBase():
    def test_ysi_dates_match_csv(self):
        for date_pair in zip(self.ysi_dataset.dates, self.ysi_csv.dates):
            assert date_pair[0] == date_pair[1], "%r != %r" % (str(date_pair[0]), str(date_pair[1]))

    def test_ysi_temps_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['water_temperature'], self.ysi_csv.temps)

#    def test_ysi_spconds_match_csv(self):
#        compare_quantity_and_csv_str(self.ysi_dataset.data['water_specific_conductance'], self.ysi_csv.spconds)

    def test_ysi_depths_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['water_depth_non_vented'], self.ysi_csv.depths)

    def test_ysi_odos_match_csv(self):
        compare_quantity_and_csv_str(self.ysi_dataset.data['water_dissolved_oxygen_percent_saturation'], self.ysi_csv.odos)


#-------------------------------------------------------------------
# Tests for ysi.YSIDataset
#-------------------------------------------------------------------
class YSIDatasetFilePath_Test(YSICompareWithCSVTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'

        self.ysi_dataset = ysi.YSIDataset(ysi_test_file_path, tzinfo=cdt)
        self.ysi_csv = ysi_csv_read(csv_test_file_path)


class YSIDatasetFileObject_Test(YSICompareWithCSVTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'

        with open(ysi_test_file_path, 'rb') as fid:
            self.ysi_dataset = ysi.YSIDataset(fid, tzinfo=cdt)

        self.ysi_csv = ysi_csv_read(csv_test_file_path)


class YSIDatasetFileObject_Test(YSICompareWithCSVTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'

        with open(ysi_test_file_path, 'rb') as fid:
            self.ysi_dataset = ysi.YSIDataset(fid, tzinfo=cdt)

        self.ysi_csv = ysi_csv_read(csv_test_file_path)


class YSIDatasetExplicitParamFile_Test(YSICompareWithCSVTestBase):
    """
    Test that data is read if param_def is explicitly specified
    """

    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'
        ysi_param_file_path = YSI_TEST_FILES_PATH + '/ysi_param.def'

        self.ysi_dataset = Sonde(ysi_test_file_path, file_format='ysi',
                                 param_file=ysi_param_file_path, tzinfo=cdt)

        self.ysi_csv = ysi_csv_read(csv_test_file_path)


def YSIDatasetNaiveDatetime_Test():
    ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'
    ysi_dataset = ysi.YSIDataset(ysi_test_file_path)

    assert ysi_dataset.dates != []


#-------------------------------------------------------------------
# Tests for the Sonde object with a file_format='ysi'
#-------------------------------------------------------------------
class SondeYSIFormatFilePath_Test(YSICompareWithCSVTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'

        self.ysi_dataset = Sonde(ysi_test_file_path,
                                 file_format='ysi', tzinfo=cdt)

        self.ysi_csv = ysi_csv_read(csv_test_file_path)



class SondeYSIFormatFileObject_Test(YSICompareWithCSVTestBase):
    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'

        with open(ysi_test_file_path, 'rb') as fid:
            self.ysi_dataset = Sonde(fid, file_format='ysi', tzinfo=cdt)

        self.ysi_csv = ysi_csv_read(csv_test_file_path)



class SondeYSIExplicitParamFile_Test(YSICompareWithCSVTestBase):
    """
    Test that data is read if param_def is explicitly specified
    """

    def setup(self):
        csv_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.csv'
        ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'
        ysi_param_file_path = YSI_TEST_FILES_PATH + '/ysi_param.def'

        self.ysi_dataset = Sonde(ysi_test_file_path, file_format='ysi',
                                 param_file=ysi_param_file_path, tzinfo=cdt)

        self.ysi_csv = ysi_csv_read(csv_test_file_path)


def SondeYSINaiveDatetime_Test():
    ysi_test_file_path = YSI_TEST_FILES_PATH + '/BAYT_20070323_CDT_YS1772AA_000.dat'
    ysi_dataset = Sonde(ysi_test_file_path, file_format='ysi')

    assert ysi_dataset.dates != []


if __name__ == '__main__':
    nose.run()

