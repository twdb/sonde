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
import numpy as np
import sonde

# setup defaults
if platform.system()=='Windows': 
    base_dir = 'T:\\BaysEstuaries\\Data\\WQData'
else:
    base_dir = '/T/SWR/BaysEstuaries/Data/WQData'

log_file_dir = 'deployment_logs'
log_file_name = 'master_deployment_log.csv'
log_file = os.path.join(base_dir, log_file_dir, log_file_name)

metadata_file = os.path.join(base_dir,'swis_site_list.psv')

disclaimer = 'test disclaimer line1\n line2 \n line3 \n'

#choose site and setup remaining variables
site_name = raw_input('Enter Site Name: ').lower()
site_dir = os.path.join(base_dir, 'sites', site_name)
original_data_files_dir = os.path.join(site_dir, 'original_data_files')

qa_rules_file = os.path.join(site_dir, 'twdb_wq_' + site_name +'_qa_rules.csv')
raw_data_file = os.path.join(site_dir,'twdb_wq_'+site_name+'_raw.csv')
clean_data_file = os.path.join(site_dir,'twdb_wq_'+site_name+'.csv')
image_file = os.path.join(site_dir,'twdb_wq_'+site_name+'.png')
image_file_wclipped = os.path.join(site_dir,'twdb_wq_'+site_name+'_withclipped.png')

if not os.path.isdir(site_dir):
    print 'No directory found for: ', site_dir
    raise

if not os.path.isdir(original_data_files_dir):
    print 'No directory found for: ', original_data_files_dir
    raise

#read in site metadata
metadata = np.genfromtxt(metadata_file, delimiter='|', dtype='|S20,|S100,|S20,|S20',
                         usecols=(1,5,6,7),
                         names='site_name,site_desc,lat,lon', skip_header=1)

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
tolower = lambda s: s.lower()
log_data = np.genfromtxt(fid, delimiter=',', dtype=None,
                         missing_values='nd',
                         autostrip=True, names=fields,
                         converters={'site_name': tolower},
                         invalid_raise=False)
fid.close()

#filter out data from other sites
log_data = log_data[log_data['site_name']==site_name]
log_dates = np.array([datetime.datetime.strptime(d+t,'%m/%d/%Y%H:%M:%S') for d,t
             in zip(log_data['date'],log_data['time'])])

#spot check data is always in local tz
log_dates = np.array([i.replace(tzinfo=sonde.find_tz(i)) for i in log_dates])

#sort deployment data
idx = np.argsort(log_dates)
log_data = log_data[idx]
log_dates = log_dates[idx]
#write sorted log data
local_log_file = os.path.join(site_dir, 'twdb_wq_' + site_name + '_deployment_log.csv')
np.savetxt(local_log_file, log_data, delimiter=',', fmt='%s') #todo fix formating and add header line

#read in original data files
data_files = glob.glob(os.path.join(original_data_files_dir,'*.*'))
data_file_names = [os.path.split(f)[-1] for f in data_files]

#check if deployment log file list matches files in original_data_files dir
log_files = log_data['renamed_filename']
if set(data_file_names)==set(log_files):
    print 'List of files in deployment logs match files found in original_data_files folder'
else:
    print 'Warning: list of data files in deployment log does not match what is found in original_data_files folder'
    print 'please check log file and fix, log file name: ', site_name + '_missing_files.txt'
    print 'for files that are not in the deployment log timezone will be applied automatically based on start_time in data'
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
for file_name in data_files:
    if file_name in log_files:
        tz_list.append(log_data['timezone'][log_data['renamed_file']==file_name])
    else:
        tz_list.append('auto')

merged_data = sonde.merge(data_files, tz_list=tz_list)

#clip data to deployment times
raw_data = copy.copy(merged_data)
for file_name,name in zip(data_files, data_file_names):
    if name not in log_data['renamed_filename']:
        print 'No data in log file, unable to clip file: ', name
        continue

    idx = np.where(name==log_data['renamed_filename'])[0]
    deploy_start_time = log_dates[idx]
    try:
        deploy_stop_time = log_dates[idx+1] #assumes no gaps in deployment log
    except:
        print 'no deploy stop time found for file: ', name
        deploy_stop_time = deploy_start_time + datetime.timedelta(365)

    clip_mask = (raw_data.dates > deploy_start_time) * \
          (raw_data.dates < deploy_stop_time) * \
          (raw_data.data_file == file_name)
    mask = clip_mask | (raw_data.data_file != file_name)
    #remove data where mask = True
    raw_data.apply_mask(mask)
    print 'Successfully clipped file: ', name

print 'writing raw data file'
raw_header = header.copy()
raw_header['qa_level']='raw uncorrected data'
raw_data.write(raw_data_file, format='csv',disclaimer=disclaimer, metadata=raw_header)

#apply qa rules
clean_data = copy.copy(raw_data)
field_names = 'site_name,start_datetime,stop_datetime,rule_name,rule_parameters,apply_to_parameters,manufacturer,serial_number,data_file'.split(',')
fmt = 9*'|S50,'
fmt = fmt[:-1]
qarules = np.genfromtxt(qa_rules_file, delimiter=',', converters={'site_name': tolower}, dtype=fmt, names = field_names)
start_dates = np.array([datetime.datetime.strptime(dt,'%m/%d/%Y %H:%M') for dt
                   in qarules['start_datetime']])
stop_dates = np.array([datetime.datetime.strptime(dt,'%m/%d/%Y %H:%M') for dt
                   in qarules['stop_datetime']])
#Apply timezone
start_dates = np.array([i.replace(tzinfo=sonde.default_static_timezone) for i in start_dates])
stop_dates = np.array([i.replace(tzinfo=sonde.default_static_timezone) for i in stop_dates])

for startdate, stopdate, qarule in zip(start_dates, stop_dates,qarules):
    print qarule
    outside_mask = ~((clean_data.dates > startdate) * (clean_data.dates < stopdate))
    if qarule['rule_name'].strip().lower()=='remove_between_limits':
        param, pmin, pmax = qarule['rule_parameters'].split('/')
        pmin = float(pmin)
        pmax = float(pmax)
        mask = (clean_data.data[param] < pmin) * (clean_data.data[param] > pmax) 

    elif qarule['rule_name'].strip().lower()=='remove_outside_limits':
        param, pmin, pmax = qarule['rule_parameters'].split('/')
        pmin = float(pmin)
        pmax = float(pmax)
        mask = (clean_data.data[param] > pmin) * (clean_data.data[param] < pmax) 
    elif qarule['rule_name'].strip().lower()=='remove_all':
        mask = outside_mask.copy()
    else:
        print 'rule_name unknown: ', qarule['rule_name']

    #apply filters
    #for filt in ['data_file','manufacturer','serial_number']:
    #    if qarule[filt] is not '':
    #        exec('mask *= clean_data.'+filt+'!=qarule[filt]')

    mask = mask | outside_mask
    parameters = qarule['apply_to_parameters'].strip()
    if parameters=='':
        clean_data.apply_mask(mask)
    else:
        clean_data.apply_mask(mask, parameters=parameters.split(','))

#write final file
clean_header = header.copy()
clean_header['qa_level']='data corrected according to rules in file ' + os.path.split(qa_rules_file)[-1]
clean_data.write(clean_data_file, format='csv',disclaimer=disclaimer, metadata=clean_header)

#create plots
