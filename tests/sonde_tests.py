# -*- coding: utf-8 -*-
"""
    Sonde Tests
    ~~~~~~~~~~~

    These tests are run to make sure Sonde is working properly.


"""
from __future__ import with_statement

import csv
from datetime import datetime
import os
import numpy as np
import re
import sys
import unittest


# Add path to sonde to sys.path for development
#sonde_path = os.path.join(os.path.dirname(__file__), '..')
#sys.path.append(os.path.join(sonde_path))

from ..sonde.formats import ysi


ysi_test_files_path = os.path.join(os.path.dirname(__file__), 'ysi_test_files')



class YSIReaderTestCase(unittest.TestCase):
    def setUp(self):

        ysi_test_file_path = ysi_test_files_path + '/BAYT_20070323_CDT_YS1772AA_000.dat'
        ysi_param_file_path = ysi_test_files_path + '/ysi_param.def'
        self.ysi_reader = ysi.YSIReader(ysi_test_file_path, param_file=ysi_param_file_path)

        csv_test_file_path = ysi_test_files_path + '/BAYT_20070323_CDT_YS1772AA_000.csv'

        csv_test_file = open(csv_test_file_path, 'rb')
        csv_reader = csv.reader(csv_test_file, delimiter=',')

        # loop through first two header lines
        for i in range(2):
            csv_test_file.next()

        date_list = []
        temp_list = []
        spcond_list = []
        depth_list = []
        odo_list = []

        for row in csv_reader:
            timestamp = row[0] + ' ' + row[1]
            date = datetime.strptime(timestamp, '%m/%d/%y %H:%M:%S')
            date_list.append(date)
            temp_list.append(row[2])
            spcond_list.append(row[3])
            depth_list.append(row[4])
            odo_list.append(row[5])

        self.dates = np.array(date_list)
        self.temps = np.array(temp_list)
        self.spcods = np.array(spcond_list)
        self.depths = np.array(depth_list)
        self.odos = np.array(odo_list)

        csv_test_file.close()

    def test_ysi_reader(self):
        for date_pair in zip(self.ysi_reader.dates, self.dates):
            assert date_pair[0] == date_pair[1], "%r != %r" % (str(date_pair[0]), str(date_pair[1]))
        


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(YSIReaderTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
