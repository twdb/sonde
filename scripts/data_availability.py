# -*- coding: utf-8 -*-
"""
script for displaying salinity data plots for given sites
the script is reading the qa/qc'ed data found in:
T:\BaysEstuaries\Data\WQData\sites\<site_name>\twdb_wq_<site_name>.csv'
"""

import os.path
import platform

from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sonde

if platform.system() == 'Windows':
    data_dir = 'T:\\BaysEstuaries\\Data\\WQData'
else:
    data_dir = '/T/BaysEstuaries/Data/WQData'

#parameters = sonde.master_parameter_list  
parameters = ['seawater_salinity', 'water_surface_elevation', 'water_ph','water_depth_non_vented',
              'water_dissolved_oxygen_concentration', 'water_dissolved_oxygen_percent_saturation',
              'water_turbidity', 'water_temperature']
estuary = 'Galveston Bay' 
"""
coastwide_sites = {'Sabine Lake': "".join('blb,sab1,midsab,usab,job,usgs1,usgs2,usgs3,usgs4,\
             jdm1,jdm2,jdm3,jdm4,mcf1,mcf2,swbr'.split()),
             'Galveston Bay': 'oldr,trin,fish,bayt,red,midg,dollar,hann,east,boli',
             'Brazos River': 'bz1u,bz2u,bz2l,bz3u,bz3l,bz5u,bz5l,bz6u,icfr',
             'San Bernard River': "".join('sb1s,sb1w,sb2s,\
             sb2w,sb3s,sb3w,sb5s,sb5w,sb6w,cowt,ced2'.split()),
             'Matagorda Bay': 'caney,eemat,ematc,ematt,umat,emath,lavc,mata',
             'San Antonio Bay': 'delt,sant,mosq,cont,chkn,mes',
             'Aransas Bay': 'cop,ara',
             'Corpus Christi Bay': "".join('nueces1,nueces2,nueces3,nueces4,\
             nueces5,nueces6,nueces7,nueces8,nueces9,nueces10,nueces11,\
             nueces12,nueces13,nueces14,nude1,nude2,nude3,ingl,ccbay,oso,\
             jfk'.split()),
            'Laguna Madre':"".join('bird,upbaff,baff,eltoro,slndcut,mans,arroyd,\
                            arroys,lm-arr,real,isabel,spcg'.split()),
            'Rio Grande River': 'rioa,riof'
            }
"""
coastwide_sites = {'Sabine Lake': "".join('blb,sab1,sab2,midsab,usab,job,swbr'.split()),
             'Galveston Bay': 'oldr,trin,fish,bayt,red,midg,dollar,hann,east,boli',
             'Brazos River': 'bz1u,bz2u,bz2l,bz3u,bz3l,bz5u,bz5l,bz6u,icfr',
             'San Bernard River': "".join('sb1s,sb1w,sb2s,\
             sb2w,sb3s,sb3w,sb5s,sb5w,sb6w,cowt,ced2'.split()),
             'Matagorda Bay': 'caney,eemat,ematc,ematt,umat,emath,lavc,mata',
             'San Antonio Bay': 'delt,sant,mosq,cont,chkn,mes',
             'Aransas Bay': 'cop,ara',
             'Corpus Christi Bay': "".join('nueces1,nueces2,nueces3,nueces4,\
             nueces5,nueces6,nueces7,nueces8,nueces9,nueces10,nueces11,\
             nueces12,nueces13,nueces14,nude1,nude2,nude3,ingl,ccbay,oso,\
             jfk'.split()),
            'Laguna Madre':"".join('bird,upbaff,baff,eltoro,slndcut,mans,arroyd,\
                            arroys,lm-arr,real,isabel,spcg'.split()),
            'Rio Grande River': 'jard,rioa,riof'
            }

estuary_sites = np.sort(coastwide_sites[estuary].split(','))

data_availability = {}
param_code = {}
#for parameter in ['water_turbidity']:
#for parameter in ['water_dissolved_oxygen_percent_saturation']:
for parameter in parameters:
    parameter_not_exist = []
    param_availability = {}
    site_param_counter = OrderedDict()
    site_counter = 1
    for site in estuary_sites:
#    for site in ['bayt', 'boli', 'midg']:
        new_sonde_filename = 'twdb_wq_' + site.strip() + '.csv'
        old_sonde_filename = 'twdb_wq_' + site.strip() + '_provisional.csv'
        new_sonde_file = os.path.join(data_dir,'sites', site, new_sonde_filename)
        old_sonde_file = os.path.join(data_dir, 'sites',site, old_sonde_filename)
        if os.path.isfile(new_sonde_file):
            sonde_file = new_sonde_file
        elif os.path.isfile(old_sonde_file):
            sonde_file = old_sonde_file
        else:
            print "No merged file exists for site: ", site + '\n' 
            continue
            
        site_sonde  = sonde.Sonde(sonde_file)

        datetimes = [pd.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                    '%m-%d-%y %H:%M:%S') for dt in site_sonde.dates]
        site_sonde_data = pd.DataFrame(site_sonde.data, index=datetimes)
        parameter_not_exist.append([parameter not in site_sonde.parameters])
        if parameter in site_sonde.parameters:
            site_sonde_data[parameter][site_sonde_data[parameter] < -900] = np.nan
            site_param_data = site_sonde_data[parameter].dropna()
            site_param_data[:] = site_counter 
            site_param_counter[site] = site_counter 
            site_counter += 1
            param_availability[site] = site_param_data.groupby(level=0).first()
        else:
          #  import pdb; pdb.set_trace()
            continue
    if np.alltrue(parameter_not_exist):
        print sonde.master_parameter_list[parameter][0] + " not available at any of the sites.\n"
        continue
    data_availability[parameter] = pd.DataFrame(param_availability)
    param_code[parameter] = site_param_counter
    
    ax = plt.figure().add_subplot(111)
    param_name = sonde.master_parameter_list[parameter][0]
    if parameter == 'water_depth_non_vented':
        param_name = "Water Depth"
    plt.title(estuary + " " + param_name + " " + "Data Availability", fontsize=14)
    data_availability[parameter].plot(style='b.', ax=ax)
    ax.set_yticks(site_param_counter.values())
    ax.set_yticklabels(site_param_counter.keys())
    ax.set_ylabel("Site Name")
    plt.legend().set_visible(False)
    plt.ylim(.5, site_param_counter.values()[-1] + .5)
    data_availability_dir = os.path.join(data_dir, 'data_availability', estuary)
    if not os.path.exists(data_availability_dir):
        os.makedirs(data_availability_dir)
#    plt.savefig(os.path.join(data_availability_dir,param_name + '.png'))

        
    
plt.show() 
    
    
                
        
            
        
        
    