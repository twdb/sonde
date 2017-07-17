import csv
from datetime import datetime
import tempfile

import xlrd


def xls_to_csv(xls_file):
    """
    Converts excel files to csv equivalents
    assumes all data is in first worksheet

    Returns a string containing the file path to a temp file
    containing the converted csv file, plus the workbook's datemode
    (useful if you need to convert dates later on)
    """
    temp_csv_fid, csv_file_path = tempfile.mkstemp()
    with open(csv_file_path, 'wb') as csv_file:
        if isinstance(xls_file, str):
            xls_file_path = xls_file
        else:
            # write out the xls_file-like object to a temp file to
            # xlrd can open it
            temp_xls_fid, xls_file_path = tempfile.mkstemp()
            xls_file.seek(0)
            with open(xls_file_path, 'wb') as temp_xls_file:
                temp_xls_file.writelines(xls_file.readlines())

        workbook = xlrd.open_workbook(xls_file_path)
        sheet = workbook.sheet_by_index(0)
        datemode = workbook.datemode

        csv_writer = csv.writer(csv_file, csv.excel)

        for row in range(sheet.nrows):
            this_row = []
            for col in range(sheet.ncols):
                val = sheet.cell_value(row, col)
                if isinstance(val, str):
                    val = val.encode('utf8')
                this_row.append(val)

            csv_writer.writerow(this_row)

    return csv_file_path, datemode


def possibly_corrupt_xls_date_to_datetime(date_val, datemode=0):
    """
    xls files generally return date columns as strings containing a
    float value, but these values can be corrupt depending on how the
    file has been saved/exported
    """
    try:
        return datetime.strptime(date_val, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        return datetime(*xlrd.xldate_as_tuple(float(date_val), datemode))
