# Main Plugin Super Class
import libsonde
import datetime
import traceback
import ysi
import quantities as pq
#from collections import defaultdict

class Dataset(libsonde.Sonde):
    
    def read_data(self):
        """ read YSI binary data files """

        self.drv_code = 'YS'
        self.drv_name = 'YSI Binary File Driver'
        
        param_map = {'Temperature' : 'TEM01',
                     'Conductivity' : 'CON02',
                     'Specific Cond' : 'CON01',
                     'Salinity' : 'SAL01',
                     'DO+' : 'DOX02',
                     'pH' : 'PHL01',
                     'Depth' : 'WSE01',
                     'Battery' : 'BAT01',
                     }

        unit_map = {'C' : pq.degC,
                    'F' : pq.degF,
                    'K' : pq.degK,
                    'mS/cm' : self.mScm,
                    'uS/cm' : self.uScm,
                    '%' : pq.percent,
                    'pH' : pq.dimensionless,
                    'meters' : pq.m,
                    'feet' : pq.ft,
                    'volts' : pq.volt,
                    }

        ysi_data = ysi.Dataset(self.filename)

        #determine parameters provided and in what units
        params = dict()
        self.data = dict()
        for parameter in ysi_data.parameters:
            try:
                pname = param_map[(parameter.name).strip()]
                punit = unit_map[(parameter.unit).strip()]
                params[pname] = punit
                self.data[param_map[parameter.name]] = parameter.data * punit
            except:
                print 'Un-mapped Parameter/Unit Type'
                print 'YSI Parameter Name:', parameter.name
                print 'YSI Unit Name:', parameter.unit
                raise

        self.set_params(params)
        self.dates = ysi_data.dates


