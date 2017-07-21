"""
   compute_water_level_filter_saliniy.py
   ~~~~~~~~

   This script is used  to:
   1- calculate water depth above pressure sensor from pressure reading and coincident barometric pressure measurements.
   2- calculate total water depth 
   3- calculate water surface elevation
   4- filter salinity when water level falls below conductivity proble as observed from corrected sonde depth (water depth above pressure sensor) measurement. 
   5- plot data
"""
import platform
import time
import os
import copy
import glob
import numpy as np
import sonde
import matplotlib.pyplot as plt
import pandas

from sonde import find_tz

if platform.system()=='Windows': 
    base_dir = 'T:\\BaysEstuaries\\Data\\WQData'
    project_dir = os.path.join('T:\\BaysEstuaries\\PROJECTS\\NUECES',
                               'Nueces Delta Ecol. Modeling_USACE',
                               '2011/Data2012-2013')
     
else:
    base_dir = '/T/BaysEstuaries/Data/WQData'
    project_dir = os.path.join('/T/BaysEstuaries/PROJECTS/NUECES',
                                'Nueces Delta Ecol. Modeling_USACE',
                                '2011/Data2012-2013')

def drop_seconds(time_series):
    """this is to realign water level and barometer timseries for adjustment"""
    return [pandas.datetime(dt.year, dt.month, dt.day,dt.hour, dt.minute) for dt in 
                            time_series.index]
def string_cleaner(string):
    if isinstance(string, str):
        return string.strip().lower()
    else:
        return string
       
        
 #the pressure in meters at which     


site_name = input('Enter Site Name: ').lower()
barologger_sitename = input('Enter Barologger Site Name: ').lower()
write_file = input("Write output file? [yes/no]: ").lower()

if barologger_sitename == 'nude3_baro':
    barologger_file_name = 'lower_delta_filled_barometer_data.csv'
if barologger_sitename == 'nueces5_baro':
    barologger_file_name = 'upper_delta_filled_barometer_data.csv'

log_file_dir = os.path.join('deployment_logs','original_files')
log_file_name = 'NUECES_DELTA_Deployment_Log_2012'
dep_log_file = os.path.join(base_dir, log_file_dir, log_file_name + 
                                    '_deployment_temp.csv')
cal_log_file = os.path.join(base_dir, log_file_dir, log_file_name + 
                                     '_calibration.csv')
site_dep_log_file = os.path.join(base_dir, log_file_dir, site_name+'_dep_log.csv')
austin_baro_file = os.path.join(project_dir, 
                                'mabry_station_and_sea_level_pressure.csv') 
sensor_to_gps_height_file = os.path.join(project_dir, 'site_coordinates.csv')
                            
sonde_site_dir = os.path.join(base_dir, 'sites', site_name)
barologger_site_dir = os.path.join(base_dir, 'sites', barologger_sitename)
sonde_data_file = os.path.join(sonde_site_dir, 'twdb_wq_' + site_name \
                                + '.csv') 
barologger_data_file = os.path.join(barologger_site_dir, barologger_file_name)

deployment_data = pandas.read_csv(dep_log_file, header=0, delimiter=',',
                                      parse_dates={'dep_datetime':[1,5],
                                                   'ret_datetime':[1,2]},
                                    na_values=['nd', '', ' ','n/a'])
calibration_data = pandas.read_csv(cal_log_file, header=0, delimiter=',', 
                                   parse_dates=[[0,2]], index_col=0,
                                    na_values=['nd', '', ' ','n/a'])
deployment_data = deployment_data.applymap(string_cleaner)
deployment_data.index = deployment_data.dep_datetime
deployment_data.rename(columns={'Height from Base of Instrument to Base of GPS Receiver          (m)':
                        'sonde_bottom_to_gps'},inplace=True)
deployment_data.rename(columns=
                        {'Depth from bottom of instrument to water surface (m) ': 
                            'sonde_bottom_to_surface'}, inplace=True)
deployment_data.rename(columns={'Total Water Depth          (m) ': 
                                    'total_water_depth'}, inplace=True)
site_deployment_data = deployment_data[deployment_data['SITE ID'] == site_name]
site_deployment_data.index = site_deployment_data.dep_datetime 
site_deployment_data['spotcheck_sensor_depth'] = np.nan 

calibration_data = calibration_data.applymap(string_cleaner)
                           
sonde_data = sonde.Sonde(sonde_data_file)
sonde_dates = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                                  '%m-%d-%y %H:%M:%S') for dt in 
                                  sonde_data.dates]
sensor_to_gps_height = pandas.read_csv(sensor_to_gps_height_file,
                                       sep=',', index_col=[0], 
                                        na_values=['nd','\s*'])
                                       
sonde_series = pandas.DataFrame(sonde_data.data,index=sonde_dates)
sonde_series['file_name'] = [f.lower().strip().split('.')[0] for f 
                            in sonde_data.data_file]
sonde_series['sonde_id'] = 'unknown'
deploy_filename_list = np.unique(sonde_series.file_name)


baro_series = pandas.read_csv(barologger_data_file, sep=',', parse_dates=[0],
                              index_col=0)
austin_lab_baro_series = pandas.read_csv(austin_baro_file, sep=',', 
                                         parse_dates=[0], index_col=0)

sonde_series.index = [pandas.datetime(dt.year, 
                                      dt.month, dt.day,dt.hour, dt.minute) 
                                      for dt in sonde_series.index]
baro_series.index = [pandas.datetime(dt.year, dt.month, dt.day,dt.hour, 
                                     dt.minute) for dt in baro_series.index]
sonde_series = sonde_series.groupby(level=0).first()
sonde_baro_series = pandas.concat((sonde_series, baro_series), 
                                  axis=1)
sonde_baro_series.water_depth_non_vented\
                [sonde_baro_series.water_depth_non_vented < -900.] = np.nan
sonde_baro_series.air_pressure[sonde_baro_series.air_pressure < -900] = np.nan
sonde_baro_series['corrected_sonde_depth'] = np.nan
sonde_baro_series['water_surface_elevation_one'] = np.nan
sonde_baro_series['water_surface_elevation_two'] = np.nan
sonde_baro_series['water_surface_elevation_three'] = np.nan
sonde_baro_series['water_surface_elevation_med'] = np.nan
sonde_baro_series['total_water_depth'] = np.nan
sonde_baro_series = sonde_baro_series.resample('15min', how='first')
ltc_zero_pressure = 9.5
ll_zero_pressure = 0.
ysi_bottom_to_sensor = .102
solinst_bottom_to_sensor = 0.01
horizontal_orientation = ['nueces2', 'nueces5', 'nueces6', 'nueces11']

water_depth_det_limit = {'nueces1': (-.2, 100.),
                               'nueces2': (0.02, 5),
                                'nueces3': (0.02, 100.),
                                'nueces4': (0.03, 100.),
                                'nueces5': (0.03, 5.),
                                'nueces6': (0.03, 40.),
                                'nueces7': (0.03, 5.),
                                'nueces8': (0.03, 100.),
                                'nueces9': (0.03, 100.),
                                'nueces10': (0.03, 100.),
                                'nueces11': (0.02, 100.),
                                'nueces12': (0.03, 100.),
                                'nueces13': (0.03, 100.),
                                'nueces14': (0.03, 100.),
                                'nude1': (0.02, 100.)}
water_depth_detection_limit = water_depth_det_limit[site_name][0]
salinity_filter_limit = water_depth_det_limit[site_name][1]


site_gps_elevation_one = sensor_to_gps_height.ix[site_name,
                                             'survey_one_elevation']
site_gps_elevation_two = sensor_to_gps_height.ix[site_name,
                                             'survey_two_elevation']
site_gps_elevation_three = sensor_to_gps_height.ix[site_name,
                                             'survey_three_elevation']
site_gps_elevation_med = sensor_to_gps_height.ix[site_name,['survey_one_elevation',
                                             'survey_two_elevation',
                                             'survey_three_elevation']].quantile(
                                             0.5)                                             
last_ret_start = pandas.datetime(2013,11,10)
last_ret_end = pandas.datetime(2013,11,15)
fig = plt.figure()
sal_ax = fig.add_subplot(111)
#sonde_baro_series.seawater_salinity.plot(style='c.', label='raw', ax=sal_ax,
#                                    markersize=4)
cleaned_sal_ax = plt.figure().add_subplot(111)
sonde_baro_series.seawater_salinity.plot(style='c.', label='removed', 
                                         ax=cleaned_sal_ax, markersize=4)
cleaned_sal_ax.set_ylim(0, 
                np.ceil(np.max([sonde_baro_series.seawater_salinity.max(),
                        site_deployment_data['SURFACE SALINITY (ppt)'].max()])))
cleaned_sal_ax.set_ylabel("salinity, psu")
cleaned_sal_ax.set_title(site_name)
plt.figure()
for sonde_file in deploy_filename_list: 
#for sonde_file in ['0912nu02']:
    deployment_specific_data = site_deployment_data[site_deployment_data\
                                ['DEPLOYED FILENAME']==sonde_file]
    sonde_type = deployment_specific_data['DEPLOYED SONDE ID']
    dep_file_mask = sonde_baro_series['file_name'] == sonde_file
    site_sonde_baro_series = sonde_baro_series[dep_file_mask] 
    sonde_baro_series['sonde_id'][dep_file_mask] = sonde_type[0]
    if 'ltc' in sonde_type.values[0]:
        print("correcting deployment file ", sonde_file)
        sonde_baro_series['corrected_sonde_depth'][dep_file_mask] = \
        sonde_baro_series.water_depth_non_vented[dep_file_mask] - \
        sonde_baro_series.air_pressure[dep_file_mask] + \
        ltc_zero_pressure
        if site_name == 'nueces13':
            if sonde_file == '0712nu13':
                survey_solinst_sonde_to_gps = 1.48
                print("solinst_to_gps,", sonde_file, survey_solinst_sonde_to_gps)
            else:
                survey_solinst_sonde_to_gps = 0.905
                print("solinst_to_gps,", sonde_file, survey_solinst_sonde_to_gps)

        else: 
            survey_solinst_sonde_to_gps = sensor_to_gps_height.ix[site_name,
                                        'median_solinst_sonde_bottom_to_gps']
        
        if site_name in horizontal_orientation:            
            site_deployment_data['spotcheck_sensor_depth'][site_deployment_data\
            ['DEPLOYED FILENAME']==sonde_file]= \
            deployment_specific_data.sonde_bottom_to_surface
            try:
                site_deployment_data.ix[last_ret_start:last_ret_end,
                    'spotcheck_sensor_depth'] = \
                site_deployment_data.sonde_bottom_to_surface.ix[last_ret_start:
                    last_ret_end][0] 
            except TypeError:
                pass
            sonde_baro_series['water_surface_elevation_one'][dep_file_mask] =\
            site_gps_elevation_one  + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            
            sonde_baro_series['water_surface_elevation_two'][dep_file_mask] =\
            site_gps_elevation_two  + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_three'][dep_file_mask] = \
            site_gps_elevation_three  + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_med'][dep_file_mask] = \
            site_gps_elevation_med  + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            
            if np.isnan(sensor_to_gps_height.ix[site_name,
                                                'median_solinst_sensor_height']):
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                                'median_ysi_sensor_height']
            else:
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                                'median_solinst_sensor_height']                       
                                            
        else:
            site_deployment_data['spotcheck_sensor_depth'][site_deployment_data\
            ['DEPLOYED FILENAME']==sonde_file]= \
            deployment_specific_data.sonde_bottom_to_surface - \
            solinst_bottom_to_sensor
            
            try:
                site_deployment_data.ix[last_ret_start:last_ret_end,
                    'spotcheck_sensor_depth'] = \
                site_deployment_data.sonde_bottom_to_surface.ix[last_ret_start:
                    last_ret_end][0] - solinst_bottom_to_sensor
            except TypeError:
                pass
            
                                                
            sonde_baro_series['water_surface_elevation_one'][dep_file_mask] = \
            site_gps_elevation_one  + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask] 
            sonde_baro_series['water_surface_elevation_two'][dep_file_mask] = \
            site_gps_elevation_two + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]      
            sonde_baro_series['water_surface_elevation_three'][dep_file_mask] = \
            site_gps_elevation_three + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]      
            sonde_baro_series['water_surface_elevation_med'][dep_file_mask] = \
            site_gps_elevation_med + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]   
            
            if site_name ==  'nueces13':
                if sonde_file == '0712nu13':
                    solinst_sensor_height = 0.29
                else: solinst_sensor_height = 0.925
            else: 
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                        'median_solinst_sensor_height'] \
                                        + solinst_bottom_to_sensor
        sonde_baro_series['total_water_depth'][dep_file_mask] = \
            solinst_sensor_height + sonde_baro_series['corrected_sonde_depth']\
            [dep_file_mask]    
#        water_depth_detection_mask = sonde_baro_series.corrected_sonde_depth\
#        < water_depth_detection_limit
#        sonde_baro_series['corrected_salinity'][dep_file_mask * \
#            water_depth_detection_mask] = np.nan
#        sonde_baro_series['total_water_depth'][dep_file_mask * \
#            water_depth_detection_mask] = -888.
            
        
    if 'ysi' in sonde_type.values[0]:
        print("correcting deployment file ", sonde_file)
        site_calibration_data = calibration_data\
                             [calibration_data['SITE ID']== site_name]
        site_dep_data = pandas.read_csv(site_dep_log_file, header=0, 
                                          sep=',',
                                          parse_dates={'dep_datetime':[1,5],
                                                   'ret_datetime':[1,2]},
                                    na_values=['nd', '', ' '])
        site_dep_data = site_dep_data.applymap(string_cleaner)
        site_dep_data.index = site_dep_data.dep_datetime 


        
#        site_cal_baro_data = pandas.concat((site_calibration_data, 
#                                           austin_lab_baro_series), axis=1)
#        site_cal_baro_data.station_pressure = site_cal_baro_data.\
#                        station_pressure.interpolate(method='linear')
#        ysi_zero_pressure_mabry = site_cal_baro_data.station_pressure.ix[site_calibration_data.index[site_calibration_data['DEPLOYED FILENAME']==sonde_file]]
        ysi_zero_pressure = site_dep_data.zero_pressure.ix[site_dep_data.index[site_dep_data['DEPLOYED FILENAME']==sonde_file]]
        sonde_baro_series['corrected_sonde_depth'][dep_file_mask] = \
        sonde_baro_series.water_depth_non_vented[dep_file_mask] - \
        sonde_baro_series.air_pressure[dep_file_mask] + ysi_zero_pressure[0]
        

        survey_ysi_sonde_to_gps = sensor_to_gps_height.ix[site_name,
                            'median_ysi_sonde_bottom_to_gps']  # this assumes that the solinst was placed at the same level of 
  
        
        if site_name in horizontal_orientation:            
            site_deployment_data['spotcheck_sensor_depth'][site_deployment_data\
            ['DEPLOYED FILENAME']==sonde_file]= \
            site_deployment_data.sonde_bottom_to_surface
            
            try:
                site_deployment_data.ix[last_ret_start:last_ret_end,
                    'spotcheck_sensor_depth'] = \
                site_deployment_data.sonde_bottom_to_surface.ix[last_ret_start:
                    last_ret_end][0] 
            except TypeError:
                pass
            
                                                          
            sonde_baro_series['water_surface_elevation_one'][dep_file_mask] = \
            site_gps_elevation_one  + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_two'][dep_file_mask] \
            = site_gps_elevation_two + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_three'][dep_file_mask] = \
            site_gps_elevation_three + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_med'][dep_file_mask] = \
            site_gps_elevation_med + sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            
            if np.isnan(sensor_to_gps_height.ix[site_name,
                                                'median_ysi_sensor_height']):
                ysi_sensor_height = sensor_to_gps_height.ix[site_name,
                                        'median_solinst_sensor_height'] 
            else:
                ysi_sensor_height = sensor_to_gps_height.ix[site_name,
                                        'median_ysi_sensor_height'] 
            
   
            
        else:
            site_deployment_data['spotcheck_sensor_depth'][site_deployment_data\
            ['DEPLOYED FILENAME']==sonde_file]= \
            deployment_specific_data.sonde_bottom_to_surface - \
            ysi_bottom_to_sensor  

            try:
                site_deployment_data.ix[last_ret_start:last_ret_end,
                    'spotcheck_sensor_depth'] = \
                site_deployment_data.sonde_bottom_to_surface.ix[last_ret_start:
                    last_ret_end][0] - ysi_bottom_to_sensor
            except TypeError:
                pass

                                              
            sonde_baro_series['water_surface_elevation_one'][dep_file_mask] = \
            site_gps_elevation_one + ysi_bottom_to_sensor +\
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_two'][dep_file_mask] = \
            site_gps_elevation_two + ysi_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_three'][dep_file_mask] = \
            site_gps_elevation_three + ysi_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            sonde_baro_series['water_surface_elevation_med'][dep_file_mask] = \
            site_gps_elevation_med + ysi_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]
            
            if np.isnan(sensor_to_gps_height.ix[site_name,
                                                'median_ysi_sensor_height']):
                ysi_sensor_height = sensor_to_gps_height.ix[site_name,
                                        'median_solinst_sensor_height']  
            else:
                ysi_sensor_height = sensor_to_gps_height.ix[site_name,
                                                    'median_ysi_sensor_height'] \
                                                        + ysi_bottom_to_sensor
        sonde_baro_series['total_water_depth'][sonde_baro_series\
        ['file_name'] == sonde_file] = ysi_sensor_height + \
        sonde_baro_series\
        ['corrected_sonde_depth'][sonde_baro_series['file_name']== sonde_file] 
     
     

    if 'll' in sonde_type.values[0]:
        sonde_baro_series['corrected_sonde_depth'][sonde_baro_series['file_name'] == sonde_file] = \
        sonde_baro_series.water_depth_non_vented[sonde_baro_series['file_name'] == sonde_file] - \
        sonde_baro_series.air_pressure[sonde_baro_series['file_name'] == sonde_file] 
        
        if np.isnan(sensor_to_gps_height.ix[site_name,
                                'median_solinst_sonde_bottom_to_gps']):
            survey_solinst_sonde_to_gps = sensor_to_gps_height.ix[site_name,
                                            'median_ysi_sonde_bottom_to_gps'] - \
                                            .25
        else :
            survey_solinst_sonde_to_gps = sensor_to_gps_height.ix[site_name,
                                    'median_solinst_sonde_bottom_to_gps']
        if site_name in horizontal_orientation:            
            site_deployment_data['spotcheck_sensor_depth'][site_deployment_data\
            ['DEPLOYED FILENAME']==sonde_file]= \
            site_deployment_data.sonde_bottom_to_surface
            
            try:
                site_deployment_data.ix[last_ret_start:last_ret_end,
                    'spotcheck_sensor_depth'] = \
                site_deployment_data.sonde_bottom_to_surface.ix[last_ret_start:
                    last_ret_end][0] 
            except TypeError:
                pass
            
 
            sonde_baro_series['water_surface_elevation_one'][dep_file_mask] = \
            site_gps_elevation_one + sonde_baro_series['corrected_sonde_depth']\
            [dep_file_mask]
            sonde_baro_series['water_surface_elevation_two'][dep_file_mask] = \
            site_gps_elevation_two + sonde_baro_series['corrected_sonde_depth']\
            [dep_file_mask]
            sonde_baro_series['water_surface_elevation_three'][dep_file_mask] = \
            site_gps_elevation_three + sonde_baro_series['corrected_sonde_depth']\
            [dep_file_mask]
            sonde_baro_series['water_surface_elevation_med'][dep_file_mask] = \
            site_gps_elevation_med + sonde_baro_series['corrected_sonde_depth']\
            [dep_file_mask]
            
            if np.isnan(sensor_to_gps_height.ix[site_name,
                                                'median_solinst_sensor_height']):
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                                        'median_ysi_sensor_height']
            else:
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                                'median_solinst_sensor_height']              
        else:
            site_deployment_data['spotcheck_sensor_depth'][site_deployment_data\
            ['DEPLOYED FILENAME']==sonde_file]= \
            deployment_specific_data.sonde_bottom_to_surface- \
            solinst_bottom_to_sensor  
            
            try:
                site_deployment_data.ix[last_ret_start:last_ret_end,
                    'spotcheck_sensor_depth'] = \
                site_deployment_data.sonde_bottom_to_surface.ix[last_ret_start:
                    last_ret_end][0] - solinst_bottom_to_sensor
            except TypeError:
                pass
            

            sonde_baro_series['water_surface_elevation_one'][dep_file_mask] = \
            site_gps_elevation_one + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]       
            sonde_baro_series['water_surface_elevation_two'][dep_file_mask] = \
            site_gps_elevation_two + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask] 
            sonde_baro_series['water_surface_elevation_three'][dep_file_mask] = \
            site_gps_elevation_three + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]  
            sonde_baro_series['water_surface_elevation_med'][dep_file_mask] = \
            site_gps_elevation_med + solinst_bottom_to_sensor + \
            sonde_baro_series['corrected_sonde_depth'][dep_file_mask]  
            
            if np.isnan(sensor_to_gps_height.ix[site_name,
                                                'median_solinst_sensor_height']):
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                        'median_ysi_sensor_height'] + .25
            else:
                solinst_sensor_height = sensor_to_gps_height.ix[site_name,
                                                'median_solinst_sensor_height'] \
                                                        + solinst_bottom_to_sensor
        sonde_baro_series['total_water_depth'][sonde_baro_series\
        ['file_name'] == sonde_file] = solinst_sensor_height + \
        sonde_baro_series\
        ['corrected_sonde_depth'][sonde_baro_series['file_name']== sonde_file]      

        
    sonde_baro_series['corrected_sonde_depth']\
    [sonde_baro_series['file_name']==sonde_file].plot(style='.',label='sonde depth')
plt.ylim(0,2)


site_deployment_data.index = [t + pandas.datetools.Hour(-1)
                            if find_tz(t).zone == 'UTC-5' else
                            t for t in site_deployment_data.index]
site_deployment_data.to_csv(os.path.join(sonde_site_dir, site_name +
                                         '_complete_dep_log.csv'),
                            sep=',', index_label='datetime(utc-6)', 
                            float_format='%10.2f', na_rep=-999.99)

site_deployment_data[site_deployment_data.columns[-3]].dropna().plot(style='r.',
                                                             markersize=12)

water_depth_detection_mask = sonde_baro_series.corrected_sonde_depth\
                            < water_depth_detection_limit
salinity_threshold_mask = sonde_baro_series.seawater_salinity < salinity_filter_limit
water_depth_detection_mask = water_depth_detection_mask * salinity_threshold_mask
sonde_baro_series['raw_seawater_salinity'] = sonde_baro_series.seawater_salinity
sonde_baro_series['seawater_salinity'][water_depth_detection_mask] = -888.88
sonde_baro_series['total_water_depth'][water_depth_detection_mask] =   -888.88
sonde_baro_series['water_surface_elevation_one'][water_depth_detection_mask] = -888.88
sonde_baro_series['water_surface_elevation_two'][water_depth_detection_mask] = -888.88
sonde_baro_series['water_surface_elevation_three'][water_depth_detection_mask] = -888.88
sonde_baro_series['water_surface_elevation_med'][water_depth_detection_mask] = -888.88
sonde_baro_series['water_temperature'][water_depth_detection_mask] = -888.88
sonde_baro_series['water_electrical_conductivity'][water_depth_detection_mask] = -888.88

site_deployment_data['spotcheck_sensor_depth'].dropna().plot(style='r^',
                                                    markersize=10,
                                                    label='spot-check')
plt.title(site_name)
plt.ylabel('depth, m')
plt.legend().set_visible(False)                                                          
#plt.ylim(0,2)
sonde_baro_series.rename(columns={'water_depth_non_vented': 
                                    'raw_pressure_reading'},inplace=True)

sonde_depth_ax = plt.figure().add_subplot(111)
sonde_baro_series.ix[:,'corrected_sonde_depth'].dropna().plot(style='b.',
    label='water depth above sensor', ax=sonde_depth_ax)    
sonde_baro_series.ix[:,'raw_pressure_reading'].dropna().plot(style='g.',
    label='raw pressure reading', ax=sonde_depth_ax)    

#site_deployment_data[site_deployment_data.columns[-3]].dropna().plot(style='r.',
#                                                             markersize=12)
site_deployment_data['spotcheck_sensor_depth'].dropna().plot(style='r.',
    markersize=10, label='spot-check',
    ax=sonde_depth_ax)

sonde_depth_ax.set_title(site_name)
sonde_depth_ax.set_ylim(0, 2)
sonde_depth_ax.set_ylabel('water depth, m')
sonde_depth_ax.legend()
#plt.savefig(os.path.join(sonde_site_dir, 
#                         site_name + '_water_depth_above_sensor.png'))
total_depth_ax = plt.figure().add_subplot(111)
#sonde_baro_series.ix[:, 'corrected_sonde_depth'].plot(style='.', ax=ax,
#                                            label='water depth above sensor')
sonde_baro_series.ix[:, 'total_water_depth'].plot(style='.', ax=total_depth_ax,
                                            label='total water depth')
total_depth_ax.set_title(site_name)
total_depth_ax.set_ylim(0,2)
total_depth_ax.set_ylabel('water depth, m')
site_deployment_data.total_water_depth.plot(style='r.', markersize=12,
                                        ax=total_depth_ax, label= 'spot-check')
plt.legend()
#plt.savefig(os.path.join(sonde_site_dir, site_name + '_water_depth.png'))
sonde_baro_series.rename(columns={'water_depth_non_vented': 
                                    'raw_pressure_reading',
                                    'seawater_salinity': 'filtered salinity',
                                    'raw_seawater_salinity': 'unfiltered salinity',
                                    'corrected_sonde_depth': 'water depth'},inplace=True)
sonde_baro_series.ix[:,['water depth', 
                        'unfiltered salinity','filtered salinity']].plot(style={'filtered salinity':'b.', 'unfiltered salinity':'c.',
                    'water depth': 'g.'}, 
                    ax=sal_ax, markersize=4,secondary_y='water depth')
#site_deployment_data['SURFACE SALINITY (ppt)'].plot(style='ro', ax=sal_ax)
sal_ax.set_ylim(0,80)
sal_ax.set_ylabel('salinity, psu')
sal_ax.set_title(site_name)
#sal_ax.right_ax.set_ylim(0.01, np.ceil(sonde_baro_series.corrected_sonde_depth.max()))
sal_ax.right_ax.set_ylim(0.01, 0.6)
sal_ax.right_ax.set_ylabel('water depth above sensor, m')

"""
site_deployment_data.total_water_depth = site_deployment_data.total_water_depth.apply(
                                    lambda d: np.float(d))
site_deployment_data.sonde_bottom_to_surface = site_deployment_data.\
                            sonde_bottom_to_surface.apply(
                                    lambda d: np.float(d))
                                    
sonde_baro_series.seawater_salinity.plot(style='b.', ax=cleaned_sal_ax,
                                         markersize=4, label="cleaned")
site_deployment_data['SURFACE SALINITY (ppt)'].plot(style='ro', 
                                 ax=cleaned_sal_ax, label='spot-check')
#plt.savefig(os.path.join(sonde_site_dir, site_name + '_salinity.png'))

sonde_baro_series.ix[:, ['water_surface_elevation_one', 
                         'water_surface_elevation_two',
                         'water_surface_elevation_three',
                         'water_surface_elevation_med']].plot(title=site_name,
                         style={'water_surface_elevation_one': '.',
                                'water_surace_elevation_two': '.',
                                'water_survace_elevation_three': '.',
                                'water_surface_elevation_med': '^'},mew=0)  
plt.ylim(-2,2)
plt.ylabel('water surface elevation,m from NAVD88') 
#plt.figure()
#sonde_baro_series.ix[:, 'water_surface_elevation_med'].plot(style='.',
 #                                                      title=site_name)  
plt.ylabel('water surface elevation,m from NAVD88')
plt.ylim(-3,1)
plt.title(site_name)

ll_bool = site_deployment_data.sonde_type == 'll'
ltc_bool = site_deployment_data.sonde_type == 'ltc'
#solinst_bool = [ll or ltc for ll,ltc in zip(ll_bool, ltc_bool)]
#solinst_sensor_height = site_deployment_data.total_depth[solinst_bool] - \
                site_deployment_data.sonde_bottom_to_surface[solinst_bool]
                
ysi_sensor_height_series = site_deployment_data.total_depth\
                        [site_deployment_data.sonde_type == 'ysi'] - \
                site_deployment_data.sonde_bottom_to_surface\
                [site_deployment_data.sonde_type == 'ysi'] 
                
try:
    solinst_sensor_height.plot(style='.-', label='solinst')
except TypeError:
    pass
try:
    ysi_sensor_height.plot(style='.-', label='ysi')
except TypeError:
    pass
"""
#plt.title(site_name + ' sensor height')
#print site_name
#print "ysi:", ysi_sensor_height.quantile(.5)
#print "solinst:", solinst_sensor_height.quantile(.5)
plt.show()

metadata_file = os.path.join(base_dir,'swis_site_list_with_nueces_added.psv')
metadata = np.genfromtxt(metadata_file, delimiter='|', dtype='|S20,|S100,|S20,|S20',
                         usecols=(1,5,6,7),
                         names='site_name,site_desc,lat,lon',skip_header=1)

idx = np.where(metadata['site_name']==site_name.upper())

if write_file == 'yes':
    disclaimer_header = ''
    disclaimer_header += 'disclaimer: This data has been collected by a Texas Water Development Board datasonde.\n'
    disclaimer_header += 'disclaimer: Raw uncorrected data may contain errors. Provisional data has had anomalous \n' 
    disclaimer_header += 'disclaimer: individual data points removed. Such data points typically are disconnected \n'
    disclaimer_header += 'disclaimer: from the recorded trend; nonetheless all removed data is retained in an associated \n'
    disclaimer_header += 'disclaimer: QA Rules file available upon request. However data that simply appear unusual are \n'
    disclaimer_header += 'disclaimer: not removed unless verifying information is obtained suggesting the data is not \n'
    disclaimer_header += 'disclaimer: representative of bay conditions. The Board makes no warranties (including no warranties \n'
    disclaimer_header += 'disclaimer: as to merchantability or fitness) either expressed or implied with respect to the data \n' 
    disclaimer_header += 'disclaimer: or its fitness for any specific application. \n'
    
    disclaimer_header += 'fill_value for bad data: -999.99. \n'
    try: 
        disclaimer_header += 'fill_value for parameters when water level falls to or below sensor level above delta bed of ' + str(solinst_sensor_height)[:5] + ' m: -888.88. \n'
    except NameError:
        disclaimer_header += 'fill_value for parameters when water level falls to or below sensor level above delta bed of ' + str(ysi_sensor_height)[:5] + ' m: -888.88. \n'
    
    disclaimer_header += 'site_description: ' + metadata['site_desc'][idx][0] + '\n'
    disclaimer_header += 'site_name: ' + site_name + '\n'
    disclaimer_header += 'latitude: ' + metadata['lat'][idx][0] + '\n'
    disclaimer_header += 'longitude: ' + metadata['lon'][idx][0] + '\n'
    
    
    disclaimer_header += 'timezone: UTC-6 \n'
    
    columnorder = ['raw_pressure_reading', 'air_pressure', 'corrected_sonde_depth',
               'total_water_depth', 'water_surface_elevation_one', 
               'water_surface_elevation_two', 'water_surface_elevation_three',
               'water_surface_elevation_med', 'water_temperature', 
               'water_electrical_conductivity', 'seawater_salinity', 'sonde_id',
               'file_name']
    processed_wq_file = os.path.join(sonde_site_dir, site_name + '_final_data_corrected.csv')
    sonde_baro_series = sonde_baro_series.ix[:, columnorder]
    fid = open(processed_wq_file, 'w')
    fid.write(disclaimer_header)
    sonde_baro_series.to_csv(fid, sep=',', index_label='datetimes', 
                             na_rep = -999.99, header=False)
    fid.close()
