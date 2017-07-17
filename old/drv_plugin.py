# Main Plugin Super Class
import numpy as np
import datetime
import traceback

class InstrumentPlugins:
    def __init__(self,filename,inboxdir,site,tz='CST'):
        """ Plugin is used to open a file """
        self.filename = filename
        self.inboxdir = inboxdir
        print('~~~~~~~~~~ reading : ' + self.filename)
        #self.outdir = outdir
        self.site = site
        self.tz = tz
        self.masterparamlist = {'Temperature' : 'degC',
                                'EC_Norm' : 'uS/cm',
                                'Salinity' : 'PSU',
                                'WaterLevel(Non_Vented)' : 'm',
                                'WaterLevel(Vented)' : 'm',
                                'BatteryVoltage' : 'V',
                                'pH' : ' ',
                                'DO' : 'mg/l',
                                '%DOSat' : '%',
                                'AirPressure' : 'mofwater',
                                'AirTemperature' : 'degC',
                                'Turbidity' : 'ntu'
                                }
        self.paramlist = {}
        self.header = []
        self.extraheader = ['## Comment: Source File: ' + self.filename +'\n',
                            '## Comment: Plugin Used: ' + self.__class__.__name__ + '\n'] #this includes comments etc.

        self.conversion_factors = {'ft' : self.ft2m,
                                   'm' : self.no_convert,
                                   'degF' : self.F2C,
                                   'degC' : self.no_convert,
                                   'NoSal_ECNorm' : self.calc_sal_ECNorm,
                                   'NoSal_EC' : self.calc_sal_EC,
                                   'NoSal_MCTD' : self.calc_sal_MCTD,
                                   'psi' : self.psi2m,
                                   'mS/cm' : self.no_convert,
                                   'uS/cm' : self.uscm2mscm,
                                   'V' : self.no_convert,
                                   'PSU' : self.no_convert,
                                   'mg/l' : self.no_convert,
                                   '%' : self.no_convert,
                                   ' ' : self.no_convert,
                                   'ntu' : self.no_convert
                                   }
        self.read_data()
        self.convert_to_CST()
        self.remove_abnormal_ECNorm()
        self.convert_data_to_common_fmt()
        #TODO ADD COMMENTS FIELD
        

    def set_params(self,plist):
        """ set list parameters and their units provided by this instrument """
        self.paramlist = plist

    def get_params(self):
        """ Return List of Parameters Provided by this plugin"""
        return self.paramlist


    def convert_to_si(self,data):
        """ Cycle through paramlist and convert units for each. Also convert Conductivity to Salinity if needed """
        for param,unit in list(self.paramlist.items()):
            #if self.conversion_factors.has_key(unit):
            #    try:
            idx = unit[1]
            #print unit[1],unit[0]
            #data[:,idx] = self.conversion_factors[unit[0]](param,data[:,idx])
            data = self.conversion_factors[unit[0]](param,data,idx)
            #except:
            #print '~~ ERROR ~~ : Either Param : ' + param + ' or unit : ' + unit[0] + ' is not implemented.'
        return data

    def convert_to_CST(self):
        """ convert all dates to CST """
        if self.tz == 'CDT':
            self.dates = self.dates - datetime.timedelta(seconds=3600)
            self.tz = 'CST'
            print('Time converted from CDT to CST')
        else:
            print('Time already in CST no conversion needed')

    def remove_abnormal_ECNorm(self):
        """ remove all rows with negative or > 100 EC Norm"""
        
        EC_idx = self.paramlist['EC_Norm'][1]
        idx = (self.data[:,EC_idx] >= 0.0)
        self.data = self.data[idx,:]
        self.dates = self.dates[idx]
        
        idx = (self.data[:,EC_idx] <= 100.0)
        self.data = self.data[idx,:]
        self.dates = self.dates[idx]
        

        
    def convert_data_to_common_fmt(self):
        """ Common Data to Common format """
        from numpy import ma
        header = ''
        unitheader = ''
        items = sorted(self.masterparamlist.items())
        for param,unit in items: #assumes this will be displayed alpabetically
            header = header + param + ', '
            unitheader = unitheader + unit + ', '
            try:
                idx = self.paramlist[param][1]
                try:
                    finaldata = ma.column_stack((finaldata,self.data[:,idx]))
                except:
                    finaldata = self.data[:,idx]
            except:
                tmp = self.data[:,0].copy()
                tmp.mask = True
                try:
                    finaldata = ma.column_stack((finaldata,tmp))
                except:
                    finaldata = tmp

        self.fieldheader = header
        self.unitheader = unitheader
        self.finaldata = ma.column_stack((self.dates,finaldata))

    def read_data(self):
        """ use numpy genfromtxt to read in data from filename """
        dates = []
        data = []
        return [dates,data]



    def write_data(self,filename):
        """ write final data to file """
        import os
        print('~~~~~~~~ writing data from ' + self.filename + ' to ' + filename)
        data = self.finaldata.filled(-999)
        dates = data[:,0]
        #convert dates to numpy array of integers
        datelist = []
        for dt in dates:
            datelist.append([dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second])
        dates = np.array(datelist)

        #get data
        data = data[:,1:data.shape[1]]

        #os.popen('echo \"## The following data have been collected by a Texas Water Development Board \" > ' + filename)
        #os.popen('echo \"## instrument. These data are raw, uncorrected, and may contain \" >> ' + filename)
        #os.popen('echo \"## errors. The Board makes no warranties (including no warranties as to \" >> ' + filename)
        #os.popen('echo \"## merchantability or fitness) either expressed or implied with respect to \" >> ' + filename)
        #os.popen('echo \"## the data or its fitness for any specific application. \" >> ' + filename)
        
        fname = open(filename,'w')
        
        fname.write('## The following data have been collected by a Texas Water Development Board\n')
        fname.write('## instrument. These data are raw, uncorrected, and may contain\n')
        fname.write('## errors. The Board makes no warranties (including no warranties as to\n')
        fname.write('## merchantability or fitness) either expressed or implied with respect to\n')
        fname.write('## the data or its fitness for any specific application.\n')
        fname.write('##\n')
        fname.write('##\n')
        fname.write('## ASCII File generated from Instrument file: ' + self.filename + '\n')
        fname.write('## Plugin used to generate ASCII File: ' + self.__class__.__name__ + '\n')
        #header = '## ASCII File generated from Instrument file: ' + self.filename
        #os.popen('echo ' + '\"' + header + '\" >> ' + filename)

        fname.write('## TWDB Site Name: ' + self.site + '\n')
        #header = '## TWDB Site Name: ' + self.site
        #os.popen('echo ' + '\"' + header + '\" >> ' + filename)

        #write site description lat & lon. This is set in processdata.py
        for line in self.header:
            fname.write(line)

        fname.write('## Timezone: ' + self.tz +'\n')
        #header = '## Timezone: ' + self.tz
        #os.popen('echo ' + '\"' + header + '\" >> ' + filename)

        fname.write('## NoData Value: -999.000000 \n')
        #header = '## NoData Value: -999.000000' 
        #os.popen('echo ' + '\"' + header + '\" >> ' + filename)

        fname.write('## Next line contains column header information \n')
        header = '# Year, Month, Day, Hour, Minute, Second, ' + self.fieldheader
        fname.write(header + '\n')
        fname.write('## Next line contains data units information \n')
        header = '## Year, Month, Day, Hour, Minute, Second, ' + self.unitheader
        fname.write(header + '\n')

        for comment in self.extraheader:
            fname.write(comment)

        fname.close()

        np.savetxt('tmpdates.txt',dates,fmt='%i',delimiter=',')
        np.savetxt('tmpdata.txt',data,fmt='%08.5f',delimiter=',')
        #os.popen('echo ' + '\"' + header + '\" >> ' + filename)
        os.popen('paste -d, tmpdates.txt tmpdata.txt >> ' + filename)
        os.popen('rm tmp*.txt')
    
    ####################################################################################################################    
    #conversion functions
    ####################################################################################################################
    def no_convert(self,param,val,idx):
        print('~ No conversion needed for ' + param + ' ~')
        return val

    ###############################################################
    def ft2m(self,param,val,idx):
        print('~ convert ft to m ~')
        self.paramlist[param] = ('m',self.paramlist[param][1])
        val[:,idx] = 0.3048*val[:,idx]
        return val

    ###############################################################
    def F2C(self,param,val,idx):
        print('~ convert Farenheit to Celcius ~')
        self.paramlist[param] = ('degC',self.paramlist[param][1])
        val[:,idx] = (5.0/9.0)*(val[:,idx]-32.0)
        return val

    ###############################################################
    def calc_sal_ECNorm(self,param,val,idx):
        """
        convert normalised conductivity to salinity NOTE MUST BE DONE LAST AFTER OTHER CONVERSIONS
        using seawater package
        
        """
        
        print('~ calculating salinity from normalized EC using seawater package~')
        from numpy import ma
        import seawater
        self.paramlist[param] = ('PSU',self.paramlist[param][1])
        T = val[:,self.paramlist['Temperature'][1]]
        cond = val[:,self.paramlist['EC_Norm'][1]]
        
        #absolute pressure in dbar
        P = val[:,self.paramlist['WaterLevel(Non_Vented)'][1]] * 1.0197 + 10.1325

        
        #if (self.paramlist['EC_Norm'][0]!='ms/cm':
        #    cond = self.conversion_factor[self.paramlist['EC_Norm'][0]][cond]

        R = cond / 42.914
        
        self.paramlist[param] = ('EC_Norm',self.paramlist[param][1])
        
        sal = seawater.salt(R,25,0)

        return (ma.column_stack((val,sal)))

    ###############################################################
    def calc_sal_EC(self,param,val,idx):
        """
        convert non normalised conductivity to salinity NOTE MUST BE DONE LAST AFTER OTHER CONVERSIONS
        using seawater package
        
        """
        
        print('~ calculating salinity from non normalised EC using seawater package~')
        from numpy import ma
        import seawater
        self.paramlist[param] = ('PSU',self.paramlist[param][1])
        T = val[:,self.paramlist['Temperature'][1]]
        cond = val[:,self.paramlist['EC_Norm'][1]]
        
        #absolute pressure in dbar
        P = val[:,self.paramlist['WaterLevel(Non_Vented)'][1]] * 1.0197 + 10.1325

        
        #if (self.paramlist['EC_Norm'][0]!='ms/cm':
        #    cond = self.conversion_factor[self.paramlist['EC_Norm'][0]][cond]

        R = cond / 42.914
        
        self.paramlist[param] = ('EC_Norm',self.paramlist[param][1])
        
        sal = seawater.salt(R,T,P)

        return (ma.column_stack((val,sal)))

    
    ###############################################################
    def calc_sal_MCTD(self,param,val,idx):
        """
        convert conductivity to salinity NOTE MUST BE DONE LAST AFTER OTHER CONVERSIONS
        http://www.coastal-usa.com/The%20Macro%20Manual.pdf
        
        """
        
        print('~ calculating MCTD salinity ~')
        from numpy import ma
        import seawater
        self.paramlist[param] = ('PSU',self.paramlist[param][1])
        T = val[:,self.paramlist['Temperature'][1]]
        cond = val[:,self.paramlist['EC_Norm'][1]]
        
        #absolute pressure in dbar
        P = val[:,self.paramlist['WaterLevel(Non_Vented)'][1]] * 1.0197 + 10.1325

        
        #if (self.paramlist['EC_Norm'][0]!='ms/cm':
        #    cond = self.conversion_factor[self.paramlist['EC_Norm'][0]][cond]

        R = cond / 42.914
        
        #sal2 = seawater.salt(R,T,P)
        #pressure correction
        F = (1.60836*pow(10,-5))*P - (5.4845*pow(10,-10))*pow(P,2) + (6.166*pow(10,-15))*pow(P,3)
        F = F / ( 1 + (3.0786*pow(10,-2))*T + (3.169*pow(10,-4))*pow(T,2) )
        R = R / (1+F)

        #Temperature Correction
        T100 = T/100.0
        R = R / (0.6765836 + 2.005294*(T100) + 1.11099*pow(T100,2) - 0.726684*pow(T100,3) + 0.13587*pow(T100,4) )

        #salinity
        self.paramlist[param] = ('EC_Norm',self.paramlist[param][1])
        sal = -0.8996 + 28.8567*R + 12.18882*pow(R,2) - 10.61869*pow(R,3) + 5.9862*pow(R,4) - 1.32311*pow(R,5) + R*(R-1)*(0.0442*T - 0.46*pow(10,-3)*pow(T,2) - 4*pow(10,-3)*R*T + (1.25*pow(10,-4) - 2.9*pow(10,-6)*T)*P )                                        
        
        return (ma.column_stack((val,sal)))

    ###############################################################
    def psi2m(self,param,val,idx):
        print('~ converting psi to meters of water ~')
        self.paramlist[param] = ('m',self.paramlist[param][1])\
        #assumes const atmospheric pressure
        val[:,idx] = (val[:,idx] - 14.7) * 0.703241 
        return val

    ###############################################################
    def uscm2mscm(self,param,val,idx):
        print('~ converting EC from uS/cm to mS/cm ~')
        self.paramlist[param] = ('mS/cm',self.paramlist[param][1])
        val[:,idx] = val[:,idx] / 1000.00 
        return val

##################################################################################################################
##################################################################################################################
#
# Individual Instrument Sub Classes
#
##################################################################################################################
##################################################################################################################
class read_GS(InstrumentPlugins):

    def read_data(self):
        """ read GreenSpan ASCII data files """

        #Note paramlist should be in same order as columns in data.
        self.set_params({'BatteryVoltage' : ('V',0),
                    'Temperature' : ('degC',1),
                    'Salinity' : ('PSU',4),
                    'EC_Norm' : ('uS/cm',3),
                    'WaterLevel(Non_Vented)' : ('m',2)                     
                    })

        filename = self.inboxdir + self.filename + '.csv'
        #read date strings
        datestr = np.genfromtxt(filename,skiprows=15,delimiter=',',usecols=[1],unpack=True,dtype='S20')
        # convert date strings to an array python dates
        # usually I woulkd use the following 
        # dates = np.array([datetime.datetime.strptime(dt,"%d/%m/%Y %H:%M:%S") for dt in datestr])
        # but some times are in the format 23:45:00 & others are 23:45
        # so we use the following loop instead
        dates = []
        for dt in datestr:
            try: 
                dates.append(datetime.datetime.strptime(dt,"%d/%m/%Y %H:%M:%S"))
            except:
                dates.append(datetime.datetime.strptime(dt,"%d/%m/%Y %H:%M"))
                
        self.dates = np.array([dates]).transpose()


        # some files have 10 columns and others have 11 so to fix do the following
        try:
            #tmp = np.genfromtxt(filename,skiprows=14,delimiter=',',usecols=[10])
            ## magic to fill missing data with -999.9
            #fillmissing = {4:lambda s: float(s or -999.9), 5:lambda s: float(s or -999.9), 6:lambda s: float(s or -999.9), 10:lambda s: float(s or -999.9)}
            #data = np.loadtxt(filename,skiprows=15,delimiter=',',usecols=(4,5,6,10),converters=fillmissing)
            data = np.genfromtxt(filename,skiprows=15,delimiter=',',usecols=(4,5,6,8,10), usemask=True)
        except:
            ## magic to fill missing data with -999.9
            #fillmissing = {3:lambda s: float(s or -999.9), 4:lambda s: float(s or -999.9), 5:lambda s: float(s or -999.9), 9:lambda s: float(s or -999.9)}
            #data = np.genfromtxt(filename,skiprows=15,delimiter=',',usecols=(3,4,5,9),converters=fillmissing)
            data = np.genfromtxt(filename,skiprows=15,delimiter=',',usecols=(3,4,5,7,9), usemask=True)

        self.data = self.convert_to_si(data)
        return [self.dates,self.data]  


##################################################################################################################
##################################################################################################################
class read_MC(InstrumentPlugins):
    
    
    def read_data(self):
        """ read MacroCTD ASCII data files """

        import os
        
        #Note paramlist should be in same order as columns in data.
        self.set_params({'BatteryVoltage' : ('V',0),
                    'Temperature' : ('degC',1),
                    'EC_Norm' : ('mS/cm',2),
                    'WaterLevel(Non_Vented)' : ('psi',3),
                    'Salinity' : ('NoSal_EC',4)                     
                    })

        filename = self.inboxdir + self.filename + '.csv'
        skiprows = os.popen("grep -n @AVERAGES "+ filename).readline()
        skiprows = int(skiprows.split(':')[0])
        #read date strings
        datestr,timestr = np.genfromtxt(filename,skiprows=skiprows,delimiter=',',usecols=[0,1],unpack=True,dtype='S20', usemask=True)
        # convert date strings to an array python dates
        # usually I woulkd use the following 
        # dates = np.array([datetime.datetime.strptime(dt,"%d/%m/%Y %H:%M:%S") for dt in datestr])
        # but some times are in the format 23:45:00 & others are 23:45
        # so we use the following loop instead
        dates = []
        for dt,tm in zip(datestr,timestr):
            try:
                dates.append(datetime.datetime.strptime(dt + ' ' + tm,"%m/%d/%Y %H:%M"))
            except:
                dates.append(datetime.datetime.strptime(dt + ' ' + tm,"%m/%d/%y %H:%M"))
                            
        self.dates = np.array([dates]).transpose()

        # read data
        data = np.genfromtxt(filename,skiprows=skiprows,delimiter=',',usecols=(2,3,4,5), usemask=True)        

        # convert to si
        self.data = self.convert_to_si(data)
        return [self.dates,self.data]  

##################################################################################################################
##################################################################################################################
class read_YS(InstrumentPlugins):
    
    
    def read_data(self):
        """ read YSI ASCII data files """

        import os
        
        #Note paramlist should be in same order as columns in data.
##       self.set_params({'BatteryVoltage' : ('V',3),
##                     'Temperature' : ('degC',0),
##                     'EC_Norm' : ('mS/cm',1),
##                     'WaterLevel(Non_Vented)' : ('m',2),
##                     'Salinity' : ('NoSal_ECNorm',4)                     
##                     })

        filename = self.inboxdir + self.filename + '.dat'
        #convert dat file to txt file
        os.popen("readysi_midge " + filename + " tmpysi.txt")  
        
        #read date
        year,month,day,hour,minute,second = np.genfromtxt('tmpysi.txt',comments='#',usecols=[0,1,2,3,4,5],unpack=True,dtype='i4', usemask=True)
        # convert date strings to an array python dates
        # usually I woulkd use the following 
        # dates = np.array([datetime.datetime.strptime(dt,"%d/%m/%Y %H:%M:%S") for dt in datestr])
        # but some times are in the format 23:45:00 & others are 23:45
        # so we use the following loop instead
        dates = [datetime.datetime(y,m,d,hh,mm,ss) for y,m,d,hh,mm,ss in zip(year,month,day,hour,minute,second)]
        self.dates = np.array(dates).transpose()

        # read data
                #read data
        try:
            #if DO data present
            data = np.genfromtxt('tmpysi.txt',comments='#',usecols=(6,7,8,9,10), usemask=True)
            #Note paramlist should be in same order as columns in data.
            self.set_params({'BatteryVoltage' : ('V',4),
                             'Temperature' : ('degC',0),
                             'EC_Norm' : ('mS/cm',1),
                             'WaterLevel(Non_Vented)' : ('m',2),
                             'Salinity' : ('NoSal_ECNorm',5),
                             'DOSat' : ('%',3)
                             })
        except:
            #if no DO data present
            data = np.genfromtxt('tmpysi.txt',comments='#',usecols=(6,7,8,9), usemask=True)
            self.set_params({'BatteryVoltage' : ('V',3),
                             'Temperature' : ('degC',0),
                             'EC_Norm' : ('mS/cm',1),
                             'WaterLevel(Non_Vented)' : ('m',2),
                             'Salinity' : ('NoSal_ECNorm',4),
                             })
        
#        data = np.genfromtxt('tmpysi.txt',comments='#',usecols=(6,7,8,9), usemask=True)        
        os.popen('rm tmpysi.txt')
        
        # convert to si
        self.data = self.convert_to_si(data)
        return [self.dates,self.data]  

##################################################################################################################
##################################################################################################################

##################################################################################################################
##################################################################################################################
class read_YS_DS(InstrumentPlugins):
    
    #TODO
    def read_data(self):
        """ read YSI ASCII data files Generated by Datasonde Upload Application"""

        import os
        
        filename = self.inboxdir + self.filename + '.txt'
        #read header info
        f = open(filename,'r') 
        while True:
            str = f.readline()
            if str[0]!='#':
                break
            if ((str.find('#File uploaded by')!=-1) or (str.find('#UserComments')!=-1)):
                self.extraheader.append('## Comment: ' + str[1:-1] + '\n')
        f.close()

        #read date
        year,month,day,hour,minute,second = np.genfromtxt(filename,comments='#',usecols=[0,1,2,3,4,5],unpack=True,dtype='i4', usemask=True)
        dates = [datetime.datetime(y,m,d,hh,mm,ss) for y,m,d,hh,mm,ss in zip(year,month,day,hour,minute,second)]
        self.dates = np.array(dates).transpose()

        #read data
        try:
            #if DO data present
            data = np.genfromtxt(filename,comments='#',usecols=(6,7,8,9,10), usemask=True)
            #Note paramlist should be in same order as columns in data.
            self.set_params({'BatteryVoltage' : ('V',4),
                             'Temperature' : ('degC',0),
                             'EC_Norm' : ('mS/cm',1),
                             'WaterLevel(Non_Vented)' : ('m',2),
                             'Salinity' : ('NoSal_ECNorm',5),
                             'DOSat' : ('%',3)
                             })
        except:
            #if no DO data present
            data = np.genfromtxt(filename,comments='#',usecols=(6,7,8,9), usemask=True)
            self.set_params({'BatteryVoltage' : ('V',3),
                             'Temperature' : ('degC',0),
                             'EC_Norm' : ('mS/cm',1),
                             'WaterLevel(Non_Vented)' : ('m',2),
                             'Salinity' : ('NoSal_ECNorm',4),
                             })
        # convert to si
        self.data = self.convert_to_si(data)
        return [self.dates,self.data]  

##################################################################################################################
##################################################################################################################

##################################################################################################################
##################################################################################################################
class read_MW(InstrumentPlugins):
    
    def read_data(self):
        """ read WEB ASCII data files from midgewater webapp """
        
        import os
        
        #Note paramlist should be in same order as columns in data.
        self.set_params({'Temperature' : ('degC',0),
                         'pH' : (' ',1),
                         'EC_Norm' : ('mS/cm',2),
                         'Salinity' : ('PSU',3),
                         'DO' : ('mg/l',4),
                         'WaterLevel(Non_Vented)' : ('m',5),
                         'Turbidity' : ('ntu',6),
                         'DOSat' : ('%',7),
                         'BatteryVoltage' : ('V',8)
                         })

        filename = self.inboxdir + self.filename + '.txt'
        #filename2 = self.inboxdir + self.filename + '.orig.txt'
        #os.open('cp ' + filename + ' ' + filename2)
        
        #read date
        year,month,day,hour,minute = np.genfromtxt(filename,comments='#',usecols=[0,1,2,3,4],unpack=True,dtype='i4', usemask=True)
        dates = [datetime.datetime(y,m,d,hh,mm,0) for y,m,d,hh,mm in zip(year,month,day,hour,minute)]
        self.dates = np.array(dates).transpose()

        # read data
        data = np.genfromtxt(filename,comments='#',usecols=(5,6,7,8,9,10,11,12,13), usemask=True,missing='-9.99')        

        #read filenames
        #fnames = np.genfromtxt(filename,comments='#',usecols=(14), usemask=True)
        
        # convert to si
        self.data = self.convert_to_si(data)
        return [self.dates,self.data]  

##################################################################################################################
##################################################################################################################
