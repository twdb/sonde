# -*- coding: utf-8 -*-
"""
script for displaying salinity data plots for given sites
the script is reading the qa/qc'ed data found in:
T:\BaysEstuaries\Data\WQData\sites\<site_name>\twdb_wq_<site_name>.csv'
"""

import os
import platform

import numpy as np
import pandas
import matplotlib.pyplot as plt

import sonde


if platform.system() == 'Windows':
    plot_dir = 'T:\\BaysEstuaries\\Data\\WQData\\sites'
    data_dir = 'T:\\BaysEstuaries\\Data\\WQData\\sites'
else:
    data_dir = '/T/BaysEstuaries/Data/WQData/sites'
#    plot_dir = '/T/BaysEstuaries/Data/WQData/sites'
    plot_dir = '/T/BaysEstuaries/USERS/SNegusse/data_requests/galveston_bay_john_mohan'
    
sites = input('Enter comma separated(no space) list of sites to plot: ').lower().strip().split(',')
start_date_str = input('\nEnter the start date(yyyy-mm-dd) of the data range to plot. \n'
                        '[Press enter to plot from first available record]: ')
end_date_str = input('\nEnter the end date(yyyy-mm-dd) of the data range to plot. \n'
                        '[Press enter to plot to end of available record]: ')                        

for site in sites:
    sonde_filename = 'twdb_wq_' + site.strip().lower() + '.csv'
    daily_sal_filename = 'twdb_' + site.strip().lower() + '_daily_salinity.csv'
    sonde_file = os.path.join(data_dir, site, sonde_filename)
    daily_sal_file = os.path.join(data_dir, daily_sal_filename)
    sonde_data  = sonde.Sonde(sonde_file)
    datetimes = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                                  '%m-%d-%y %H:%M:%S') for dt in 
                                  sonde_data.dates]
    sal_series = pandas.Series(sonde_data.data['seawater_salinity'], 
                               index=datetimes)
#    sal_series[sal_series < -900] = np.nan
    sal_series[sal_series < 0.2] = np.nan
    sal_series = sal_series.dropna()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sal_series.plot(style='.', ax=ax)
    plt.ylabel('salinity, psu')
    plt.title(site)
    if len(start_date_str) == 0:
        start_date = sal_series.index[0]
    else:
        start_date = pandas.datetime.strptime(start_date_str, '%Y-%m-%d')
    if len(end_date_str) == 0:
        end_date = sal_series.index[-1]
    else:
        end_date = pandas.datetime.strptime(end_date_str, '%Y-%m-%d')
    plt.xlim(start_date, end_date)
    plt.ylim(0,60)
#    plt.grid(b=None)
    plot_file_name = site + '_salinity.png'
    plot_file = os.path.join(plot_dir, plot_file_name) 
    plt.savefig(plot_file)

plt.show()