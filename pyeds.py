'''
pyeds - Python Environmental Data System

'''

#import numpy as np
#import re
from collections import defaultdict
import datetime
import traceback

import libsonde


#read in config file
config_obj=libsonde.PyedsConfig()
config = config_obj.load_config('pyeds.conf')

#load available drivers for different instrument types based on values in config
loaded_drivers = defaultdict()
for driver_code,driver_name in config['driver'].iteritems():
    try:
        driver=__import__(driver_name)
        try:
            loaded_drivers[driver_code] = driver.Dataset
            #eval('config[\'loaded_drivers\'][driver_code] = driver')
        except:
            pass
    except ImportError:
        print 'Cannot find driver ',driver_name




