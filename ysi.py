# module to read ysi binary format
import struct
import re
import numpy as np
from StringIO import StringIO
import time
import datetime

class ChannelRec:
    def __init__(self, rec, param_def):
        self.sonde_channel_num = rec[0]
        self.sensor_type = rec[1]
        self.probe_type = rec[2]
        self.zero_scale = rec[3]
        self.full_scale = rec[4]
        self.name = param_def[rec[1]][1]
        self.unit = param_def[rec[1]][2]
        self.unitcode = param_def[rec[1]][3]
        self.ndecimals = param_def[rec[1]][4]
        self.data = []

class Dataset:
    def __init__(self, filename, param_file='ysi_param.def'):
        """ opens filename and reads in ysi data """
        self.filename = filename
        self.num_params = 0
        self.parameters = []
        self.julian_time = []
        self.read_param_def(param_file)
        self.read_ysi()
        self.ysi_epoch = time.mktime((1984,03,01,0,0,0,0,0,-1))
        for param in self.parameters:
            param.data = (np.array(param.data)).round(decimals=param.ndecimals)
            
        self.dates = []
        for t in self.julian_time:
            self.dates.append(datetime.datetime.fromtimestamp(t + self.ysi_epoch))

        self.dates = np.array(self.dates)
        self.julian_time = np.array(self.julian_time)
        self.begin_log_time =  datetime.datetime.fromtimestamp(self.begin_log_time + self.ysi_epoch)
        self.first_sample_time =  datetime.datetime.fromtimestamp(self.first_sample_time + self.ysi_epoch)

    def read_param_def(self, filename):
        fid = open(filename)
        file_string = fid.read()
        file_string = re.sub("\n\s*\n*", "\n", file_string) #remove blank lines
        file_string = re.sub(";.*\n*", "", file_string) #remove comment lines
        file_string = re.sub("\t", "", file_string) #remove tabs
        file_string = re.sub("\"", "", file_string) #remove quotes
        self.ysi_file_version = int(file_string.splitlines()[0].split('=')[-1])
        self.ysi_num_param_in_def = int(file_string.splitlines()[1].split('=')[-1])
        self.ysi_ecowatch_version = int(file_string.splitlines()[2].split('=')[-1])
        dtype = np.dtype([('ysi_id', '<i8'),
                          ('name', '|S20'),
                          ('unit', '|S11'),
                          ('shortname', '|S9'),
                          ('num_dec_places', '<i8')])
        self.ysi_param_def = np.genfromtxt(StringIO(file_string), delimiter=',', usecols=(0,1,3,5,7) , skiprows=3, dtype=dtype)
        
    def read_ysi(self):
        fid = open(self.filename)
        type = []
        self.num_params=0
        while 1:
            type = fid.read(1)
            #fid.seek(-1,1)
        
            if not type:
                break

            if type=='A':
                fmt = '<HLH16s32s6sLll36s'
                fmt_size = struct.calcsize(fmt)
                self.instr_type, self.system_sig, self.prog_ver, \
                                 self.serial_num, site_name, self.pad1,\
                                 self.logging_interval, self.begin_log_time, \
                                 self.first_sample_time, self.pad2 \
                                 = struct.unpack(fmt,fid.read(fmt_size))
                
            elif type=='B':
                self.num_params = self.num_params + 1
                fmt = '<hhHff'
                fmt_size = struct.calcsize(fmt)
                self.parameters.append(ChannelRec(struct.unpack(fmt,fid.read(fmt_size)),self.ysi_param_def))
                
            elif type=='D':
                fmt = '<l' + str(self.num_params) + 'f'
                fmt_size = struct.calcsize(fmt)
                recs = struct.unpack(fmt,fid.read(fmt_size))
                self.julian_time.append(recs[0])
                for ii in range(self.num_params):
                    self.parameters[ii].data.append(recs[ii+1])
                
            else:
                print 'Type not implemented yet:',type
                break
        fid.close()

