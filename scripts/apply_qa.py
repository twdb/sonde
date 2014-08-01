"""
   apply_qa
   ~~~~~~~~

   This script allows you to view data and apply qa rules.
   it generates final data ready to be sent to customer
"""
import platform
import time
import os
import copy
import glob
import datetime
import sys
sys.dont_write_bytecode = True
import numpy as np
import sonde
import matplotlib.pyplot as plt
import pandas

site_description = {'sab2': 'Sabine Lake',
                    'midg': 'Galveston Bay',
                    'trin': 'Trinity Bay',
                    'mosq': 'San Antonio Bay',
                    'ingl': 'Corpus Christi Bay',
                    'spcg': 'Lower Laguna Madre',
                    'mata': 'Matagorda Bay'}

def apply_qa_rule(sonde_data, start_date, stop_date, qa_rule, qa_params, param_to_qa):
    """function for removing bad values from wq data 
    arguments:
    data = Sonde object
    start_dates and stop_dates=single or list of datetime time objects.
    method = a string or list of strings defining the rule for removing
    data. 
    The three available methods are:
    'remove_inside_limits/pmin/pmax' --> remove values of parameter
    p between pmin and pmax
    'remove_outside_limits/pmin/pmax' --> remove values of parameter p
    outside the values pmin and pmax
    'remove_all' --> remove all parameters between the start_dates
    and end_dates"""
    outside_mask = ~((sonde_data.dates > start_date) * (sonde_data.dates < stop_date))
    if qa_rule.strip().lower()=='remove_between_limits':
        param, pmin, pmax = qa_params.split('/')
        pmin = float(pmin)
        pmax = float(pmax)
        mask = ~(sonde_data.data[param] < pmin) * (sonde_data.data[param] > pmax) 

    elif qa_rule.strip().lower()=='remove_outside_limits':
        param, pmin, pmax = qa_params.split('/')
        pmin = float(pmin)
        pmax = float(pmax)
        mask = (clean_data.data[param] > pmin) * (clean_data.data[param] < pmax) 
    elif qa_rule.strip().lower()=='remove_all':
        mask = outside_mask.copy()
    else:
        print 'rule_name unknown: ', qa_rule

    #apply filters
    #for filt in ['data_file','manufacturer','serial_number']:
    #    if qarule[filt] is not '':
    #        exec('mask *= clean_data.'+filt+'!=qarule[filt]')
    mask = mask | outside_mask
    if np.all(mask):
        print 'No data altered for rule: ', qa_rule
    else:
        print str(np.where(mask==False)[0].size) + \
        ' entries altered for rule: ', qa_rule
        parameters = param_to_qa.strip()
        if parameters=='':
            sonde_data.apply_mask(mask)
        else:
            sonde_data.apply_mask(mask, parameters=parameters.split(','))
    return sonde_data



start_date = ''  #local datetimes
end_date = ''

# setup defaults
if platform.system()=='Windows': 
    base_dir = 'T:\\BaysEstuaries\\Data\\WQData'
else:
    base_dir = '/T/BaysEstuaries/Data/WQData'

log_file_dir = 'deployment_logs'
log_file_name = 'master_deployment_log.csv'
log_file = os.path.join(base_dir, log_file_dir, log_file_name)

metadata_file = os.path.join(base_dir,'swis_site_list.psv')

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


#choose site and setup remaining variables
site_name = raw_input('Enter Site Name: ').lower()
site_dir = os.path.join(base_dir, 'sites', site_name)
original_data_files_dir = os.path.join(site_dir, 'original_data_files')

error_log_file = os.path.join(site_dir, 'read_errors.txt')
qa_rules_file = os.path.join(site_dir, 'twdb_wq_' + site_name +'_qa_rules.csv')
raw_data_file = os.path.join(site_dir,'twdb_wq_'+site_name+'_raw.csv')
clean_data_file = os.path.join(site_dir,'twdb_wq_'+site_name+'.csv')
image_file = os.path.join(site_dir,'twdb_wq_'+site_name+'.png')
image_file_wclipped = os.path.join(site_dir,'twdb_wq_'+site_name+'_withclipped.png')

if not os.path.isdir(site_dir):
    #print 'No directory found for: ', site_dir
    raise

if not os.path.isdir(original_data_files_dir):
    #print 'No directory found for: ', original_data_files_dir
    raise

#read in site metadata
metadata = np.genfromtxt(metadata_file, delimiter='|', dtype='|S20,|S100,|S20,|S20',
                         usecols=(1,5,6,7),
                         names='site_name,site_desc,lat,lon',skip_header=1)

idx = np.where(metadata['site_name']==site_name.upper())
header = {}
header['site_name'] = site_name
header['site_description'] = metadata['site_desc'][idx][0]
header['latitude'] = metadata['lat'][idx][0]
header['longitude'] = metadata['lon'][idx][0]

#read deployment log data
fid = open(log_file)
buf = fid.readline()
while buf:
    if buf.strip('# ').lower()[0:9]=='site_name':
        fields = buf.replace(' ','').strip('#\r\n').split(',')
        # todo read in units
        break
    buf = fid.readline()

fid.seek(0)
tolower = lambda s: s.strip().lower()
strip = lambda s: s.strip()
dtype = [('site_name','S32'),
         ('date', 'S32'),
         ('time', 'S32'),
         ('water_temperature', 'float'),
         ('seawater_electrical_conductivity', 'float'),
         ('salinity', 'float'),
         ('ph', 'float'),
         ('water_dissolved_oxgyen_concentration', 'float'),
         ('water_dissolved_oxygen_saturation', 'float'),
         ('water_depth_non_vented', 'float'),
         ('instrument_battery_voltage', 'float'),
         ('spotcheck_instrument_serial_number', 'S32'),
         ('deployed_instrument_serial_number', 'S32'),
         ('deployed_DO_serial_number', 'S32'),
         ('deployed_filename', 'S60'),
         ('renamed_filename', 'S60'),
         ('timezone', 'S6'),
         ('field_tech_name', 'S32'),
         ('created_by', 'S32'),
         ('verified_by', 'S32'),
         ('qa_status', np.int32),
         ('notes', 'S60')]
log_data = np.genfromtxt(fid, delimiter=',', dtype=dtype,
                         comments="somethingthatnoonewilleveruse",
                         autostrip=True, names=fields,
                         converters={'site_name': tolower,'renamed_filename': strip},
                         invalid_raise=True)
fid.close()

#filter out data from other sites
log_data = log_data[log_data['site_name']==site_name]
log_dates = np.array([datetime.datetime.strptime(d+t,'%m/%d/%Y%H:%M:%S') for d,t
             in zip(log_data['date'],log_data['time'])])

#spot check data is always in local tz & convert to default static tz
log_dates = np.array([i.replace(tzinfo=sonde.find_tz(i)) for i in log_dates])

tmp_datetimes = np.array([(i.strftime('%m/%d/%Y %H:%M:%S').split()) for i in log_dates])
try:
    log_data['date'] = tmp_datetimes[:,0]
    log_data['time'] = tmp_datetimes[:,1]
except:
    pass
#sort deployment data
idx = np.argsort(log_dates)
log_data = log_data[idx]
log_dates = log_dates[idx]
#write sorted log data
log_file_name = os.path.join(site_dir, 'twdb_wq_' + site_name + '_deployment_log.csv')
local_log_file = open(log_file_name, 'wb')
local_log_file.write('#file_format: pysonde deployment log version 1.0 \n # site_name, date, time, water_temperature, seawater_electrical_conductivity, salinity, ph, water_dissolved_oxygen_concentration, water_dissolved_oxygen_saturation, water_depth_non_vented,intrument_battery_voltage, spotcheck_instrument_serial_number, deployed_instrument_serial_number,deployed_DO_serial_number, deployed_filename, renamed_filename, timezone, field_tech_name, created_by, verified_by, notes \n # n/a, mm/dd/yyyy, hh:mm:ss, degC, mS/cm, psu, nd, mg/l, %, mH2O,volts, n/a, n/a,n/a, n/a,n/a,n/a,n/a,n/a,n/a,n/a \n')

np.savetxt(local_log_file, log_data, delimiter=',', fmt='%s') 
local_log_file.close()

#read in original data files
data_files = glob.glob(os.path.join(original_data_files_dir,'*.*'))
data_files = [str(f) for f in data_files]
data_file_names = [os.path.split(f)[-1] for f in data_files]

#check if deployment log file list matches files in original_data_files dir
log_files = log_data['renamed_filename']
if set(data_file_names)==set(log_files):
    print 'List of files in deployment logs match files found in original_data_files folder'
else:
    #print 'Warning: list of data files in deployment log does not match what is found in original_data_files folder'
    #print 'please check log file and fix, log file name: ', site_name + '_missing_files.txt'
    #print 'for files that are not in the deployment log timezone will be applied automatically based on start_time in data'
    missing_files_log = os.path.join(site_dir, site_name + '_missing_files.txt')
    fid = open(missing_files_log, 'w')
    fid.write('log file written: ' + time.ctime() + '\n')
    files_err1 = list(set(data_file_names) - set(log_files))
    files_err2 = list(set(log_files) - set(data_file_names))
    fid.write('Files in original_data_files folder that are missing in deployment log:\n')
    for file_name in files_err1:
        fid.write(file_name + '\n')

    fid.write('Files in deployment log that are missing in original_data_files folder:\n')
    for file_name in files_err2:
        fid.write(file_name + '\n')
    fid.close()

#merge original data files
tz_list = []
for file_name in data_file_names:
    if file_name in log_files:
        tz = log_data['timezone'][log_data['renamed_filename']==file_name][0]
        if tz.strip()=='' or tz.strip().lower()=='nd':
            #print 'No timezone specified in deployment log, assuming auto:', file_name 
            tz = 'auto'
        tz_list.append(tz)
    else:
        tz_list.append('auto')

merged_data = sonde.merge(data_files, tz_list=tz_list)

#clip data to deployment times
raw_data = copy.copy(merged_data)
for file_name in np.unique(raw_data.data_file):
    if file_name not in log_data['renamed_filename']:
        #print 'Filename not found in deployment log, unable to clip file: ', file_name
        continue

    idx = np.where(file_name==log_data['renamed_filename'])[0]
    deploy_start_time = log_dates[idx]
    try:
        deploy_stop_time = log_dates[idx+1] #assumes no gaps in deployment log
    except:
        #print 'no deploy stop time found for file: ', file_name
        deploy_stop_time = deploy_start_time + datetime.timedelta(365)
    outside_mask = ~(raw_data.data_file == file_name)

    clip_mask = (raw_data.dates > deploy_start_time) * \
          (raw_data.dates < deploy_stop_time) * \
          (raw_data.data_file == file_name)

    mask = clip_mask | outside_mask
    raw_data.apply_mask(mask)
    #print str(np.where(mask==False)[0].size) + ' entries clipped from file: ', file_name

#print 'writing raw data file'
raw_header = header.copy()
raw_header['qa_level']='raw uncorrected data'
raw_data.write(str(raw_data_file), file_format='csv',disclaimer=disclaimer, metadata=raw_header, float_fmt='%5.3f')

#apply qa rules
clean_data = copy.copy(raw_data)
field_names = 'site_name,start_datetime,stop_datetime,rule_name,\
rule_parameters,apply_to_parameters,manufacturer,serial_number,data_file'.split(',')
fmt = 9*'|S50,'
fmt = fmt[:-1]

if os.path.exists(qa_rules_file):
    try:
        qarules = np.genfromtxt(qa_rules_file, delimiter=',', 
                                converters={'site_name': tolower}, 
                                dtype=fmt, names = field_names)
#need to make 0-d arrays iterable by adding 1 dim.
        qarules = np.array(qarules, ndmin=1)
        
        for qarule in qarules:
            #print qarule
            startdate = datetime.datetime.strptime(qarule['start_datetime'],
                                                   '%m/%d/%Y %H:%M')
            stopdate = datetime.datetime.strptime(qarule['stop_datetime'],
                                                  '%m/%d/%Y %H:%M')
            startdate = startdate.replace(tzinfo=sonde.default_static_timezone)
            stopdate = stopdate.replace(tzinfo=sonde.default_static_timezone)
#            import pdb; pdb.set_trace()
            clean_data = apply_qa_rule(clean_data, startdate, stopdate, 
                                       qarule['rule_name'], 
                                       qarule['rule_parameters'],
                                       qarule['apply_to_parameters'])
    except IOError:
        pass    



#write final file
print 'writing clean data file'
clean_header = header.copy()
clean_header['qa_level']='provisional data corrected according to QA rules in file ' + os.path.split(qa_rules_file)[-1]
if start_date:
    start_date = datetime.datetime.strptime(start_date,'%Y-%m-%d %H:%M') 
#    start_date_time = start_date.replace(tzinfo=sonde.find_tz(start_date))
else:
    start_date_time = raw_data.dates[0]
if end_date:
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d %H:%M')
#    end_date_time = end_date.replace(tzinfo=sonde.find_tz(end_date))
else:
    end_date_time = raw_data.dates[-1]

#data_range_mask = (clean_data.dates >= start_date_time) * (clean_data.dates <= end_date_time)
#clean_data.apply_mask(data_range_mask)
clean_data.write(clean_data_file, file_format='csv',disclaimer=disclaimer, metadata=clean_header,
                 float_fmt='%5.3f')

#create plots
#read in data @todo fix copy.copy problems
raw_data = sonde.Sonde(str(raw_data_file))
clean_data = sonde.Sonde(str(clean_data_file))


raw_dates = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                                  '%m-%d-%y %H:%M:%S') for dt in raw_data.dates]
raw_series = pandas.DataFrame(raw_data.data,index=raw_dates)
raw_series['filename'] = raw_data.data_file

clean_dates = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                                  '%m-%d-%y %H:%M:%S') for dt in clean_data.dates]
clean_series = pandas.DataFrame(clean_data.data,index=clean_dates)
clean_series['filename'] = clean_data.data_file

log_dates = [pandas.datetime.strptime(dt.strftime('%m-%d-%y %H:%M:%S'), 
                                      '%m-%d-%y %H:%M:%S' ) for dt in log_dates]
spot_series = pandas.DataFrame(log_data,index=log_dates)


#salinity plots
#plt.figure(site_name.upper() + "Salinity")
#site_descriptions = {'emath': 'GIWW near Matagorda Harbor',
#                     'ematt': 'Old Tide Gage',
#                     'ematc': 'Shellfish Marker C',
#                     'eemat': 'East End of East Matagorda Bay',
 # 
#                   'caney': 'Caney Creek'}

clean_series = clean_series.groupby(level=0).first()
try:
    clean_sal_series = clean_series['seawater_salinity']
    raw_sal_series = raw_series['seawater_salinity']
    spotcheck_sal_series = spot_series['salinity']
    #clean_sal_series = clean_sal_series.asfreq('Min')
    site_sal_ax = plt.figure().add_subplot(111)
    raw = raw_sal_series.plot(style='c.', mec='c', label='raw data', 
                              markersize=4, ax=site_sal_ax)
    clean = clean_sal_series.plot(style='b.',mec='b', label='QAed data',
                                  markersize=4, ax=site_sal_ax)
    if spotcheck_sal_series.size != 0:
        S = spotcheck_sal_series.plot(style='ro',mec='r',label='spot check')  
    plt.legend(loc='best')
    ymax = clean_sal_series.max() + 2
#    plt.xlim(pandas.datetime(2012,1,1))
    site_sal_ax.set_ylim(0, ymax)
    site_sal_ax.set_ylabel('Salinity,ppt')
#    plt.title("Salinity at " + site_descriptions[site_name] + '(' + site_name  + ')')
    plt.title("Salinity at " +  site_name.upper())
    
    plt.savefig(image_file)
    print "plotted raw vs qa'ed salinity"


    dep_sal_ax = plt.figure().add_subplot(111)
#    plt.title('OLDR salinity - unique color per deployment')


    filename_list = np.unique(clean_series['filename'])
    for sonde_file in filename_list:      
        clean_sal_series = clean_sal_series.groupby(level=0).first()
        sonde_sal_series = clean_sal_series[clean_series.filename==sonde_file]
        sonde_sal_series.plot(style='.', ax=dep_sal_ax)

    """
    i = 1
    if spotcheck_sal_series.size != 0:
        S = spotcheck_sal_series.plot(style='ro',mec='r',label='spot check')  
    for filename in filename_list.sort_index():
        idx = clean_series['filename'] == filename
        deployment_series = clean_series[idx]
        deployment_series['qa_status'] = clean_sal_series.max() + 1.5
        if filename.strip() in log_data['renamed_filename']:
#            print "qa status for file ", filename, " found"
            qa_status = log_data['qa_status'][log_data['renamed_filename'] == filename.strip()][0]  
        else:
            print "qa status for file ", filename, " not found."
            if deployment_series.index[0] < pandas.datetime(2008,1,1): #assuming data before 2008 is at least stage 2.
                qa_status = 2
            else:
                qa_status = 1
                   
        if qa_status == 1:
            deployment_series['qa_status'].plot(style='r-',linewidth=3)
        elif qa_status == 2:
            deployment_series['qa_status'].plot(style='y-',linewidth=3)
        elif qa_status == 3:
            deployment_series['qa_status'].plot(style='g-',linewidth=3)
        
        date_list = []
   
        if i%2 == 0:
            deployment_series['seawater_salinity'].plot(style='b.', mew=0,
                                                        raise_on_error=False)
        if i%2 == 1:
            deployment_series['seawater_salinity'].plot(style='c.', mew=0,
                                                        raise_on_error=False)
        i += 1
    """
    if spotcheck_sal_series.size != 0:
        S = spotcheck_sal_series.plot(style='ro',mec='r',label='spot check')  
    
 #   plt.ylim(0,50)
#    plt.xlim(start_date_time, end_date_time)
    dep_sal_ax.set_ylabel('Salinity,psu')
    dep_sal_ax.set_ylim(0, ymax)
    dep_sal_ax.set_title(site_name.upper() + ' Salinity')
    plt.grid(True, which='major')
#    plt.legend()
    #print "plotted qa'ed salinity with unique deployment colors"
except KeyError:
  pass
    

try:
    raw_wsl_series = raw_series['water_depth_non_vented']
    clean_wsl_series = clean_series['water_depth_non_vented']
    site_wsl_ax = plt.figure().add_subplot(111)
#    raw = raw_wsl_series.plot(style='c.', mec='c', label='raw data', markersize=4)
#    clean = clean_wsl_series.plot(style='b.',mec='b', label='QAed data', markersize=4)
    plt.legend(loc='best')
    site_wsl_ax.set_ylabel('Water level, m')
    site_wsl_ax.set_title(site_name.upper())
    raw_wsl_series.plot(style='c.', label='raw', ax=site_wsl_ax)
    clean_wsl_series.plot(style='b.', label="qa'ed", ax=site_wsl_ax)
    site_wsl_ax.set_title(site_name.upper())
    site_wsl_ax.set_ylim(0,np.ceil(clean_wsl_series.max()))
    site_wsl_ax.set_xlim(clean_series.index[0], clean_series.index[-1])
    site_wsl_ax.set_ylabel('water depth above sonde, m')
    dep_wsl_ax = plt.figure().add_subplot(111)
    filename_list = np.unique(clean_series['filename'])
    for sonde_file in filename_list:      
        clean_wsl_series = clean_wsl_series.groupby(level=0).first()
        sonde_wsl_series = clean_wsl_series[clean_series.filename==sonde_file]
        sonde_wsl_series.plot(style='.', ax=dep_wsl_ax)
    dep_wsl_ax.set_title(site_name.upper())
    dep_wsl_ax.set_xlim(clean_series.index[0], clean_series.index[-1])
    dep_wsl_ax.set_ylim(0,np.ceil(clean_wsl_series.max()))
    dep_wsl_ax.set_ylabel('absolute pressure reading, m')
    #print "plotted water surface elevation"
except KeyError:
    #print "no water level data found"
    pass
#plt.savefig(image_file_wclipped)
#plt.savefig(image_file)


plt.show()

