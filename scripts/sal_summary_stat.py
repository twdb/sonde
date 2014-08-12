# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 16:16:33 2013

@author: snegusse
"""
import os
import platform

import numpy as np
import pandas
import matplotlib.pyplot as plt

import sonde
if platform.system() == 'Linux':
    data_dir = '/T/BaysEstuaries/Data/WQData/sites'
    plot_dir = '/T/BaysEstuaries/USERS/SNegusse/drought_workshop_032014'
if platform.system() == 'Windows':
    data_dir = 'T:\\BaysEstuaries\\Data\\WQData\\sites'
    plot_dir = 'T:\\BaysEstuaries\\USERS\\SNegusse\\drought_workshop_032014'
    
sites = 'sab1,sab2,bayt,trin,midg,boli,lavc,mata,delt,sant,mosq,tcsalt3,ingl,tcbaff,tcbird'.split(',')
#sites = ['cowt','sb1w','sb2w','sb3w','sb5w']
#sites = ['tcbird']
annual_mean = {}
annual_max = {}
annual_std = {}

disclaimer = ''
disclaimer += 'This data has been collected by a Texas Water Development Board datasonde.\n'
disclaimer += 'Raw, uncorrected data may contain errors. Provisional data has had anomalous \n' 
disclaimer += 'individual data points removed. Such data points typically are disconnected \n'
disclaimer += 'from the recorded trend; nonetheless, all removed data is retained in an associated \n'
disclaimer += 'QA Rules file available upon request. However, data that simply appear unusual are \n'
disclaimer += 'not removed unless verifying information is obtained suggesting the data is not \n'
disclaimer += 'representative of bay conditions. The Board makes no warranties (including no warranties \n'
disclaimer += ' as to merchantability or fitness) either expressed or implied with respect to the data \n' 
disclaimer += 'or its fitness for any specific application. \n'

year1 = 2011
year2 = 2013
year3 = 2012

for site in sites:
    sonde_filename = 'twdb_wq_' + site.strip().lower() + '.csv'
    daily_sal_filename = 'twdb_' + site.strip().lower() + '_daily_salinity.csv'
    sonde_file = os.path.join(data_dir, site, sonde_filename)
    daily_sal_file = os.path.join(data_dir, daily_sal_filename)
    sonde_data  = sonde.Sonde(sonde_file)
    datetimes = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                                  '%m-%d-%y %H:%M:%S') for dt in 
                                  sonde_data.dates]
    sal_series = pandas.Series(sonde_data.data['seawater_salinity'].magnitude, 
                               index=datetimes)
#    sal_series[sal_series < -900] = np.nan
    sal_series[sal_series < 0.2] = np.nan
    sal_series = sal_series.dropna()
    daily_sal_series = sal_series.resample('D', how='mean')
    
#    fid = open(daily_sal_file,'w')
#    fid.write(disclaimer)
#    daily_sal_series.to_csv(fid, header=['salinity, psu'], 
#                            index_label='Date/time', na_rep='NA', 
#                            float_format='%10.2f')
#    fid.close()
        
    
    
    
    monthly_sal_series = sal_series.resample('M', how='mean')
    monthly_grouped_till_2010 = sal_series.ix[:pandas.datetime(2010,12,31)].groupby(lambda d: d.month)
    monthly_mean_till_2010 = monthly_grouped_till_2010.mean()
#    monthly_grouped_w_2011 = sal_series.ix[:pandas.datetime(2013,12,31)].groupby(lambda d: d.month)  
#    monthly_averages_wo_2011 = monthly_grouped_wo_2011.mean()
#    monthly_averages_w_2011 = monthly_grouped_w_2011.mean()   
    monthly_grouped_2011_2013 = sal_series.ix[pandas.datetime(2011,1,1):
                                                pandas.datetime(2013,12,1)].\
                                            groupby(lambda d: d. month)
    monthly_grouped_historical = sal_series.groupby(lambda d: d.month)
    monthly_median_2011_2013 = monthly_grouped_2011_2013.quantile(.5)
    monthly_mean_2011_2013 = monthly_grouped_2011_2013.mean()
    monthly_median_historical = monthly_grouped_historical.quantile(.5)
    monthly_mean_historical = monthly_grouped_historical.mean()
    monthly_min_historical = monthly_grouped_historical.min()
    monthly_max_historical = monthly_grouped_historical.max()

    sal_series_year1 = sal_series.ix[pandas.datetime(year1,1,1):
                                     pandas.datetime(year1,12,31)]
    sal_series_year2 = sal_series.ix[pandas.datetime(year2,1,1):
                                    pandas.datetime(year2,12,31)]
    sal_series_year3 = sal_series.ix[pandas.datetime(year3,1,1):
                                    pandas.datetime(year3,12,31)]

#    grouped_year1 = sal_series_year1.groupby(lambda d: d.month)
#    grouped_year2 = sal_series_year2.groupby(lambda d: d.month)
#    monthly_max_year1 = grouped_year1.max()
 #   monthly_max_year2 = grouped_year2.max()d
 #   monthly_min_year1 = grouped_year1.min()
    monthly_mean_year1 = monthly_sal_series.ix[pandas.datetime(year1,1,1):
                    pandas.datetime(year1,12,31)]
    monthly_mean_year2 = monthly_sal_series.ix[pandas.datetime(year2,1,1):
                    pandas.datetime(year2,12,31)]
    monthly_mean_year3 = monthly_sal_series.ix[pandas.datetime(year3,1,1):
                    pandas.datetime(year3,12,31)]
    monthly_mean_year1.index = np.arange(1,monthly_mean_year1.size + 1)
    monthly_mean_year2.index = np.arange(1,monthly_mean_year2.size + 1)
    monthly_mean_year3.index = np.arange(1,monthly_mean_year3.size + 1)
#    yerr_low = (monthly_mean_year1 - monthly_min_year1).values
#    yerr_hi = (monthly_max_year1 - monthly_mean_year1).values
#    hist_stat = sal_series.ix[:pandas.datetime(year2,12,31)].describe()
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


    
    """
    plt.figure()
    plt.title("salinity at " + site)
#    sal_series.plot(style='b-', label='raw')
    daily_sal_series.plot(style='b-', label='daily')
    plt.ylim(0,45)
    plt.ylabel('salinity, psu')
    plot_filename = site + '_' + 'daily_salinity.png'
#    plt.savefig(os.path.join(plot_dir, plot_filename))
    """    
    
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
#    monthly_averages_2012.plot(ax=ax, style='ms-', xticks=xticks,
 #                         label='mean (2012)')
#    plt.errorbar(monthly_averages_2011.index, monthly_averages_2011.values, 
#                 yerr=[yerr_low, yerr_hi],fmt='r-')


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
    """
    ax1 = plt.figure().add_subplot(111)
    plt.title('historical vs 2011 and maximum hourly salinity at ' + site)
    monthly_max_wo_2011.plot(ax=ax1, style='bs-', xticks=xticks,
                     label=str(sal_series.index[0].year) + \
                        '-' + '2010')
    monthly_max_year1.plot(ax=ax1, style='rs-', xticks=xticks,label='2011')
#    monthly_max_year2.plot(ax=ax1, style='ms-', xticks=xticks, label='2012')
    plt.ylim(0,75)
    plt.xlim(0.9, 12.1)
    plt.ylabel('salinity, psu')
    ax1.set_xticklabels(mon_labels)
    plt.legend(loc='best')
    plt.grid('on')
    plot_filename = site + '_' + str(year1) + '_monthly_max.png'
#   plt.savefig(os.path.join(plot_dir, plot_filename))
    

    ax2 = plt.figure().add_subplot(111)
#    plt.title('monthly mean salinity at ' + site)
    monthly_averages_wo_2011.plot(ax=ax2, style='bs-', xticks=xticks,
                     label=str(sal_series.index[0].year) + \
                        '-' + '2010')
    monthly_averages_w_2011.plot(ax=ax2, style='rs-', xticks=xticks,
                 label=str(sal_series.index[0].year) + \
                        '-' + '2011')
    plt.ylim(0,45)
    plt.xlim(0.9, 12.1)
    plt.ylabel('salinity, psu')
    plt.xlabel('date')
    ax2.set_xticklabels(mon_labels)
    plt.legend(loc='best')
    plt.grid('on')
    plot_filename = site + '_mean_trend_w_and_wo_2011.tif'
#    plt.savefig(os.path.join(plot_dir, plot_filename), dpi=200, format='tiff')
#    monthly_average.ix[pandas.datetime(year1,1,1):]
    """

annual_mean_df = pandas.DataFrame(annual_mean).T.ix[sites,:]
annual_std_df = pandas.DataFrame(annual_std).T.ix[sites,:]
annual_max_df = pandas.DataFrame(annual_max).T.ix[sites,:]



#galveston_sites = ['bayt', 'trin', 'midg', 'boli']
#sa_sites = ['delt', 'sant', 'mosq', 'chkn', 'cont']
#N = len(sa_sites)
#ind = np.arange(N*2,step=2)
#width = 0.5
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
plt.savefig(os.path.join(plot_dir, 'lower_coast_mean_barchart_color_blind.png'), 
            orientation='landscape', dpi=200)
"""
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
