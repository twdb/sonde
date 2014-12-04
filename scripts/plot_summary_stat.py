#!/usr/bin/env python
"""
script to generate wq summary statistics plot and csv file for sites with period of record of at least *five* years.  
- this will give meaningful stat 
- best to run this from the project/data request directory since that's where it will save files.
- not well tested for cases where the historical dataset doesn't have a minimum of one record of each day of the year. 

Usage:
    plot_summary_stat.py <parameter> <site_list> <averaging> [--save-plot --save-txt --ymin=<ymin> --ymax=<ymax> --recent_years=<number>]

Options:
    -h --help                   show this screen
    <parameter>                 parameter to plot. currently plots
                                - salinity
                                - temperature
                                - depth
                                - ph
                                - DO
                                - turbidity
    <averaging>                 monthly or daily
    <site_list>                 comma separated(no space) list of sites to plot
                                wq parameter for.
    --save-plot                 save plot in current working directory
    --save-txt                  save summary statistics in current working directory
    --ymin=<ymin>               min limit of y-axis. default is maximum data value
    --ymax=<ymax>               max limit of y-axis. default is minimum data value
    --recent_years=<number>     the number of most recent years to plot with historical plot. default is three.
    --plot-title                optional plot title. if not given site name is used.


Example:
    run /home/snegusse/sonde/scripts/plot_summary_stat temperature midg,trin --ymin=0 --ymax=30

"""
from calendar import month_name
import os
import platform
import warnings

from docopt import docopt
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt


import sonde

if platform.system() == 'Linux':
    data_dir = '/T/BaysEstuaries/Data/WQData/sites'

if platform.system() == 'Windows':
    data_dir = 'T:\\BaysEstuaries\\Data\\WQData\\sites'


param_map = {'depth': 'water_depth_non_vented',
             'do': 'water_dissolved_oxygen_concentration',
             'ph': 'water_ph',
             'salinity': 'seawater_salinity',
             'temperature': 'water_temperature',
             'turbidity': 'water_turbidity',
             }

def _calculate_historical_statistics(sonde_file, parameter, averaging,
                                    recent_years=3):
    sonde_data = _read_sonde_data(sonde_file)
    sonde_param_data = sonde_data[parameter]
    sonde_param_data[sonde_param_data < -900] = np.nan

    sonde_param_data[np.logical_and(sonde_param_data.index.month==2,
                                    sonde_param_data.index.day==29)] = np.nan
    sonde_param_data.dropna(inplace=True)


    final_year = sonde_param_data.index.year[-1]
    first_year = sonde_param_data.first_valid_index().year
    year_str = '(%s - %s)' % (first_year, final_year-1)

    historical_enddate = pd.datetime(final_year - 1, 12, 31, 23, 59)
    historical_data = sonde_param_data.ix[:historical_enddate]
    if averaging == 'monthly':
        grouped_monthly_data = historical_data.groupby(lambda d: d.month)
        hist_stat = grouped_monthly_data.describe()
        hist_stat = pd.DataFrame({
        'min':  grouped_monthly_data.min(),
        'mean': grouped_monthly_data.mean(),
        'max': grouped_monthly_data.max()})
        for year_ago in np.arange(recent_years):
            start_date = pd.datetime(final_year - year_ago, 1, 1)
            end_date = pd.datetime(final_year - year_ago, 12, 31, 23, 59)
            monthly_mean = _calculate_mean(sonde_param_data.ix[start_date:end_date], 'M')
            hist_stat[str(start_date.year)] = pd.DataFrame(monthly_mean.values,
                index=monthly_mean.index.month)
    else:
        grouped_daily_data = historical_data.groupby(lambda d:
            (d.month, d.day))
        hist_stat = pd.DataFrame({
            'min':  grouped_daily_data.min(),
            'mean': grouped_daily_data.mean(),
            'max': grouped_daily_data.max()})
        try: 
            hist_stat.index = np.arange(1,366)   #requiring historical data to have a minimum of one record for each day of year.
        except ValueError:
            raise ValueError("The merged data file %s doesn't have the minimum required record length of five years." % sonde_file)
        
        for year_ago in np.arange(recent_years):
            start_date = pd.datetime(final_year - year_ago, 1, 1)
            end_date = pd.datetime(final_year - year_ago, 12, 31, 23, 59)
            daily_mean = _calculate_mean(sonde_param_data.ix[start_date:end_date], 'D')
            daily_mean.index = daily_mean.index.dayofyear
            hist_stat[str(start_date.year)] = pd.DataFrame(daily_mean.values,
                index=daily_mean.index)

    hist_stat.year_range = year_str
    hist_stat.final_year = final_year
    hist_stat.first_year = first_year

    return hist_stat

def _calculate_mean(sonde_series, frequency):
    return sonde_series.resample(frequency)

#def generate_stat_file(sonde_file, parameter, recent_years=3):

def plot_statistics(sonde_file, parameter, averaging, recent_years=3, ymin=None,
                    ymax=None, title=None):
    _set_mpl_params()
    historical_stat = _calculate_historical_statistics(sonde_file, parameter,
        averaging=averaging, recent_years=recent_years)
    hist_max = historical_stat['max']
    hist_mean = historical_stat['mean']
    hist_min = historical_stat['min']

    figure = plt.figure(edgecolor='none')
    plt.title(title)
    ax = figure.add_subplot(111)
    figure.patch.set_alpha(.1)
    if averaging == 'monthly':
        xticks = np.arange(0.5,12.5)
    if averaging == 'daily':
        #generating random non-leap year arbitrary year to easily pick first day of month
        is_first_day_of_month = pd.date_range(start='2005-01-01', end='2005-12-31',
            freq='D').day == 1
        xticks = historical_stat.index[is_first_day_of_month]

    mon_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
                  'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ax.xaxis.set_ticklabels(mon_labels)
    hist_max.plot(ax=ax, style='k-.', xticks=xticks,label='max ' + historical_stat.year_range)
    hist_mean.plot(ax=ax, style='-.', xticks=xticks, label='mean ' + historical_stat.year_range,
        markersize=3,  color='#8C6B6E', linewidth=3)
    hist_min.plot(ax=ax, style='k--', xticks=xticks, label='min ' + historical_stat.year_range)

    ax.fill_between(hist_mean.index, hist_min, hist_max,
                    facecolor='#FCFBE3', alpha=0.3, linewidth=0)

    plot_props = [(0, '#2C4C61', 'o'),
                  (1, '#1693A5', 's'),
                  (2, '#ACBEB3', 'D')]
    year_handles_labels = []
    if  0 < recent_years and recent_years <= 3:
        for year_ago, color, marker  in plot_props[:recent_years]:
            year = historical_stat.final_year - year_ago
            historical_stat[str(year)].plot(ax=ax, style = '-', xticks=xticks,
                color=color, label='mean ' + str(year))
            if averaging == 'monthly':
                historical_stat[str(year)].plot(ax=ax, style='.', xticks=xticks,
                marker=marker, color=color)
            if averaging == 'daily':
                is_day_15_of_month = pd.date_range(start='2005-01-01',
                    end='2005-12-31', freq='D').day == 15
                historical_stat[str(year)].ix[is_day_15_of_month].plot(ax=ax, style='.',
                    marker=marker, color=color)
            year_handles_labels.append(
                (matplotlib.lines.Line2D([0, 1], [0, 1], color=color,
                    marker=marker, markeredgewidth=0), str(year)))

        year_handles_labels = year_handles_labels[::-1]

        first_legend =  ax.legend(*zip(*year_handles_labels),
            frameon=False, numpoints=1, ncol=len(year_handles_labels),
            loc='lower center', bbox_to_anchor=(0.3, -0.225))
        ax.add_artist(first_legend)
        all_handles = ax.get_legend_handles_labels()
        ax.legend(all_handles[0][:3], all_handles[1][:3],
            loc='lower center', bbox_to_anchor=(0.83, -0.275), frameon=False)
        figure.subplots_adjust(bottom=0.20)
        if averaging == 'monthly':
            ax.set_xlim(0.5,12.5)
        else:
            ax.set_xlim(1, 365)
        if ymin:
            ax.set_ylim(ymin=float(ymin))
        if ymax:
            ax.set_ylim(ymax=float(ymax))
        param_name = sonde.master_parameter_list[param_code][0]
        param_unit = sonde.master_parameter_list[param_code][1].symbol
        ax.set_ylabel(param_name + ', ' + param_unit)
        return ax
    elif recent_years == 0:
        all_handles = ax.get_legend_handles_labels()
        ax.legend(all_handles[0][:3], all_handles[1][:3],
            loc='lower center', bbox_to_anchor=(0.83, -0.275), frameon=False)
        figure.subplots_adjust(bottom=0.20)
        if averaging == 'monthly':
            ax.set_xlim(0.5,12.5)
        if averaging == 'daily':
            ax.set_xlim(1, 365)
        if ymin:
            ax.set_ylim(ymin=float(ymin))
        if ymax:
            ax.set_ylim(ymax=float(ymax))
        param_name = sonde.master_parameter_list[param_code][0]
        param_unit = sonde.master_parameter_list[param_code][1].symbol
        ax.set_ylabel(param_name + ', ' + param_unit)
        return ax

    else:
        raise NotImplementedError("please select a maximum of three recent years to plot")

def save_stat_data(hist_stat_df, output_file, averaging):
    year_range = hist_stat_df.year_range
    hist_stat_df.rename(columns={'min': 'min' + '_' + year_range,
        'mean': 'mean' + '_' + year_range,
        'max': 'max' + '_' + year_range}, inplace=True)
    if averaging == 'monthly':
        hist_stat_df.index = [month_name[m] for m in hist_stat_df.index]
        hist_stat_df.to_csv(output_file, sep=',', float_format="%5.2f", index_label='Month')

    if averaging == 'daily':
        hist_stat_df.index = pd.date_range(
            start='2005-01-01', end='2005-12-31', freq='D')     #proper datetime index with arbitrary year to generate Mon-day labels in file. 
        hist_stat_df.to_csv(output_file, sep=',', float_format='%5.2f',
            index_label='Month-Day', date_format='%b-%d')
        
def _read_sonde_data(sonde_file):
    sonde_data  = sonde.Sonde(sonde_file)
    datetimes = [pd.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'),
                                  '%m-%d-%y %H:%M:%S') for dt in
                                  sonde_data.dates]
    sonde_df = pd.DataFrame(sonde_data.data,
                               index=datetimes)
    return sonde_df

def _set_mpl_params():
    matplotlib.rcdefaults()
    params = {
        'axes.labelsize': 12,
        'font.family': 'serif',
        'font.weight': 'normal',
        'font.size': 12,
        'legend.fontsize': 11,
        'lines.linewdith': 3,
        'lines.markeredgewidth': 0,
        'lines.markersize': 6,
        'text.fontsize': 12,
        'usetex': False,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        }

    matplotlib.rcParams.update(params)

if __name__ == '__main__':
    args = docopt(__doc__)

    parameter = args['<parameter>']
    param_code = param_map[parameter]
    if parameter not in param_map.keys():
        raise ValueError("Unknown wq parameter. Check the help menu for list of parameters.")
    sites = args['<site_list>'].lower().split(',')
    averaging = args['<averaging>']
    if args['--recent_years']:
        recent_years = int(args['--recent_years'])
    ymin = args['--ymin']
    ymax = args['--ymax']

    for site in sites:
        sonde_file = os.path.join(data_dir, site, 'twdb_wq_' + site + '.csv')
        if not os.path.exists(sonde_file):
            warnings.warn("Sonde file %s could not be found" % sonde_file)
            continue

        sonde_parameters = sonde.Sonde(sonde_file).parameters
        if param_code not in sonde_parameters:
            warnings.warn("Parameter %s not found in %s" % (parameter, site))
            continue

        plot_statistics(sonde_file, param_code, averaging,
            recent_years=recent_years, ymin=ymin, ymax=ymax,
            title=site.upper())

        if args['--save-txt']:
            historical_stat = _calculate_historical_statistics(sonde_file,
                param_code, averaging, recent_years=recent_years)
            output_dir = os.getcwd()
            output_file = os.path.join(output_dir,  site + '_historical_stat.csv')
            save_stat_data(historical_stat, output_file, averaging)
            print "Historical statistics saved in file: %s" % output_file

"""
for site in sites:
    sal_series_year1 = sal_series.ix[pandas.datetime(year1,1,1):
                                     pandas.datetime(year1,12,31)]
    sal_series_year2 = sal_series.ix[pandas.datetime(year2,1,1):
                                    pandas.datetime(year2,12,31)]
    sal_series_year3 = sal_series.ix[pandas.datetime(year3,1,1):
                                    pandas.datetime(year3,12,31)]


    hist_stat_til_2010 = sal_series.ix[:pandas.datetime(2010,12,31)].describe()
    site_year1_stat = sal_series_year1.describe()
    site_year2_stat = sal_series_year2.describe()
    site_year3_stat = sal_series_year3.describe()

    annual_mean[site] = pandas.Series([hist_stat_til_2010['mean'],
        site_year1_stat.ix['mean'], site_year2_stat.ix['mean'],
        site_year3_stat.ix['mean']],
        index=['historical', str(year1), str(year2), str(year3)]).T
#    annual_std[site] = pandas.Series([hist_stat.ix['std'],
#                                     site_year_stat.ix['std']],
#                                    index=['historical', '2011']).T
#    annual_max[site] = pandas.Series([hist_stat.ix['max'],
#                                 site_year_stat.ix['max']],
#                                index=['historical', '2011']).T
    xticks = np.arange(1,13)
    mon_labels = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul',
                  'aug', 'sep', 'oct', 'nov', 'dec']






    ax =  plt.figure().add_subplot(111)
    plt.title(site.upper() + ' Monthly Mean Salinities')
#    series_to_plot.plot(ax=ax, style='r-', xticks=xticks, label=str(year1))
    monthly_mean_historical.plot(ax=ax, style = 'sb-', xticks=xticks, linewidth=2,
                          label= 'mean ' + str(sal_series.index[0].year) + '-' +
                          str(sal_series.index[-1].year), markersize=3)
#    monthly_mean_2011_2013.plot(ax=ax, style = 'sr-', xticks=xticks,
#                          label= str(year1) + '-' +  str(year2))
    monthly_min_historical.plot(ax=ax, style='k--', xticks=xticks,
                     label='min ' + str(sal_series.index[0].year) +
                     '-' + str(sal_series.index[-1].year))
    monthly_max_historical.plot(ax=ax, style='k-.', xticks=xticks,label='max ' +
                            str(sal_series.index[0].year) + '-' +
                   str(sal_series.index[-1].year))
    monthly_mean_year1.plot(ax=ax, style = 'sr-', xticks=xticks, markersize=3,
                            label='mean ' + str(year1))
    monthly_mean_year3.plot(ax=ax, style = 'sg-', xticks=xticks, markersize=3,
                            label='mean ' + str(year3))
    monthly_mean_year2.plot(ax=ax, style = 'sc-', xticks=xticks, markersize=3,
                            label='mean ' + str(year2))



    plt.ylim(0,80)
    plt.xlim(0.9,12.1)
#    monthly_median.plot(ax=ax, style='c-', xticks=xticks, label='median')
    ax.set_xticklabels(mon_labels)
    ax.legend(loc='best')
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1,
    box.width, box.height * 0.9])

# Put a legend below current axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1),
          fancybox=True, shadow=True, ncol=6, fontsize=8)
    plt.xlabel("")
    plt.ylabel('salinity, psu')
    plt.grid('on')
#    plot_filename = site + '_' + str(year2) + '_monthly_mean_2011-2013.png'
    plot_filename = site + '_' + '2011-2013_mean.png'

#    plt.savefig(os.path.join(plot_dir, plot_filename), dpi=200)


annual_mean_df = pandas.DataFrame(annual_mean).T.ix[sites,:]
annual_std_df = pandas.DataFrame(annual_std).T.ix[sites,:]
annual_max_df = pandas.DataFrame(annual_max).T.ix[sites,:]

upper_coast_sites = 'sab1,sab2,bayt,trin,midg,boli'.split(',')
middle_coast_sites = 'lavc,mata,delt,sant,mosq'.split(',')
lower_coast_sites = 'tcsalt3,ingl,tcbaff,tcbird'.split(',')

N = len(lower_coast_sites)
ind = np.arange(N*5,step=5)
width = 1.
ax = plt.figure().add_subplot(111)
plt.title('Mean Salinities at Lower Coast Sites')
plt.axvspan(9.5,30,facecolor='0.5', alpha=0.3)
#plt.axvspan(15.5,21.5, facecolor='0.5', alpha=0.5)
#plt.axvspan(25.5,30, facecolor='0.5', alpha=0.5)

#rects1 = ax.bar(ind, annual_mean_df['historical'].ix[sites],
#                width, color='b',
#                yerr=annual_std_df['historical'].ix[sites], ecolor='k')
#rects2 = ax.bar(ind+width, annual_mean_df['2011'].ix[sites], width, color='r',
#                yerr=annual_std_df['2011'].ix[sites], ecolor='k')
rects1 = ax.bar(ind, annual_mean_df['historical'].ix[lower_coast_sites],
                width, color='k')
rects2 = ax.bar(ind+width, annual_mean_df[str(year1)].ix[lower_coast_sites],
                width, color='#ACBEB3')
rects3 = ax.bar(ind+2*width, annual_mean_df[str(year3)].ix[lower_coast_sites],
                width, color='#1693A5')
rects4 = ax.bar(ind+3*width, annual_mean_df[str(year2)].ix[lower_coast_sites],
                width, color='#2C4C61')

ax.set_ylabel('salinity, psu')
#    ax.legend(loc='best')
box = ax.get_position()
ax.set_position([box.x0, box.y0 + box.height * 0.1,box.width, box.height * 0.9])

ax.legend((rects1[0], rects2[0], rects3[0], rects4[0]),
          ('historical', year1, year3, year2), bbox_to_anchor=(0.5, -0.13),
      fancybox=True, shadow=True, ncol=6, fontsize=10, loc='upper center')

ax.set_xticks(ind+2*width)
ax.set_xticklabels(lower_coast_sites)
#ax.annotate('Sabine-Neches', xy=(0.075, 0.65), xycoords='axes fraction')
#ax.annotate('Trinity-San Jacinto', xy=(0.55, 0.65), xycoords='axes fraction')
#ax.annotate('Lavaca-Colorado', xy=(0.395, 0.86), xycoords='axes fraction')
#ax.annotate('Guadalupe', xy=(0.57, 0.86), xycoords='axes fraction')
#ax.annotate('Lavaca-Colorado', xy=(0.075, 0.86), xycoords='axes fraction')
#ax.annotate('Guadalupe', xy=(0.55, 0.86), xycoords='axes fraction')
#ax.annotate('Nueces', xy=(0.755, 0.86), xycoords='axes fraction')
#ax.annotate('Laguna Madre', xy=(0.88, 0.88), xycoords='axes fraction')
ax.annotate('Nueces', xy=(0.23, 0.95), xycoords='axes fraction')
ax.annotate('Laguna Madre', xy=(0.65, 0.95), xycoords='axes fraction')

plt.xlim(0,N*5)
plt.ylim(0,55)
plt.grid('on')
plt.xlabel('sites')
#plt.savefig(os.path.join(plot_dir, 'lower_coast_mean_barchart_color_blind.png'),
#            orientation='landscape', dpi=200)

N = len(sites)
ind = np.arange(N*2,step=2)
width = 0.5
ax = plt.figure(figsize=(11,8.5)).add_subplot(111)
#plt.title('Historical and 2011 maximum salinity')
plt.axvspan(3.5,11.5,facecolor='0.5', alpha=0.3)
plt.axvspan(15.5,19.5, facecolor='0.5', alpha=0.3)
rects1 = ax.bar(ind, annual_max_df['historical'].ix[sites],
                width, color='b')
rects2 = ax.bar(ind+width, annual_max_df['2011'].ix[sites], width, color='r')
ax.set_ylabel('salinity, psu')
ax.legend((rects1[0], rects2[0]),('historical',
                                   '2011'), loc='best', fontsize=8)
ax.set_xticks(ind+width)
ax.set_xticklabels(sites)
ax.annotate('Sabine-Neches', xy=(0.01, 0.95), xycoords='axes fraction')
ax.annotate('Trinity-San Jacinto', xy=(0.22, 0.95), xycoords='axes fraction')
ax.annotate('Lavaca-Colorado', xy=(0.54, 0.95), xycoords='axes fraction')
ax.annotate('Guadalupe', xy=(0.75, 0.85), xycoords='axes fraction')
ax.annotate('Nueces', xy=(0.91, 0.85), xycoords='axes fraction')

plt.xlim(0,N*2)
plt.ylim(0,75)
plt.grid('on')
plt.xlabel('sites')

#plt.savefig(os.path.join(plot_dir, 'all_sites_max_bar_barchart.tif'),
#            orientation='landscape', dpi=200, format='tiff')
"""
plt.show()
