#!/usr/bin/env python
"""
script for displaying sonde data plots

Usage: 
    plot_sites_parameter.py <parameter> <site_list> [--ymin=<ymin> --ymax=<ymax> --sdate=<sdate> --edate=<edate> --save-plot] 
    
Options:
    -h --help                   show this screen
    <parameter>                 parameter to plot. currently plots 
                                - salinity
                                - temperature
                                - depth
                                - ph
                                - DO 
    <site_list>                 comma separated(no space) list of sites to plot
                                wq parameter for. 
    --ymin=<ymin>               min limit of y-axis
    --ymax=<ymax>               max limit of y-axis 
    --sdate=<sdate>             start date for plot in format: yyyy-mm-dd
    --edate=<edate>             end date for plot in format: yyyy-mm-dd
    --save-plot                 save plot in current working directory

Example:
    run /home/snegusse/sonde/scripts/plot_sites_salinity.py temperature midg,trin --ymin=0 --ymax=30 --sdate=2008-01-01 --edate=2009-01-01
"""

import datetime
from docopt import docopt
import os
import platform
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas

import sonde


if platform.system() == 'Windows':
    plot_dir = 'T:\\BaysEstuaries\\Data\\WQData\\sites'
    data_dir = 'T:\\BaysEstuaries\\Data\\WQData\\sites'
else:
    data_dir = '/T/BaysEstuaries/Data/WQData/sites'

parameter_map = {'salinity': 'seawater_salinity',
                 'temperature': 'water_temperature',
                 'pH': 'water_ph',
                 'turbidity': 'water_turbidity',
                 'depth': 'water_depth_non_vented',
                 'do': 'water_dissolved_oxygen_concentration'}

#parameter = raw_input("Enter sonde parameter to plot:")
    
#sites = raw_input('Enter comma separated(no space) list of sites to plot: ').lower().strip().split(',')
args = docopt(__doc__)
parameter = args['<parameter>']
if parameter.lower() not in list(parameter_map.keys()):
    raise LookupError("parameter %s is not available for plotting" % parameter)
param_unit = sonde.master_parameter_list[parameter_map[parameter]][1].symbol
sites = args['<site_list>']


for site in sites.split(','):
    site = site.lower()
    sonde_filename = 'twdb_wq_' + site.strip().lower() + '.csv'
    sonde_file = os.path.join(data_dir, site, sonde_filename)    
    if not os.path.exists(sonde_file):
        warnings.warn("File %s could not be found" % sonde_file)
        continue    
    sonde_data  = sonde.Sonde(sonde_file)

    if parameter_map[parameter] not in sonde_data.parameters:
        warnings.warn("Parameter %s not found in %s" % (parameter, site))
        continue
    
    datetimes = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                        '%m-%d-%y %H:%M:%S') for dt in sonde_data.dates]
    sonde_series = pandas.Series(sonde_data.data[parameter_map[parameter]], 
                           index=datetimes)
                           
    sonde_series[sonde_series < -900] = np.nan

    if sonde_series.size == 0:
        warnings.warn("Empty parameter series. Check the file for site %s" % site)
        continue
        
    sonde_series = sonde_series.dropna()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sonde_series.plot(style='.', ax=ax)
    plt.ylabel(parameter + ',' + param_unit)
    plt.title(site)
    if  args['--ymin']:
        plt.ylim(ymin=float(args['--ymin']))
    if args['--ymax']:
        plt.ylim(ymax=float(args['--ymax']))
    
    if args['--sdate']:
        sdate = datetime.datetime.strptime(args['--sdate'], '%Y-%m-%d')
        plt.xlim(xmin=sdate)
    if args['--edate']:
        edate = datetime.datetime.strptime(args['--edate'], '%Y-%m-%d')
        plt.xlim(xmax=edate)
#    plt.grid(b=None)
    if args['--save-plot']:
        plot_file = os.path.join(os.getcwd(), site + '_' + parameter + '.png')
        plt.savefig(plot_file)
        print('%s plot for site %s saved in %s' % (parameter, site, plot_file))
              
plt.show()