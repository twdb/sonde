"""
    sonde.quantities
    ~~~~~~~~~~~~~~~~

    This module contains a few custom quantities that are used
    primarily for unit conversion.
"""
from __future__ import absolute_import
import quantities as pq

#: unit of electrical potential
mvolt = pq.UnitQuantity('Milivolts',
                      pq.CompoundUnit("mV"),
                      symbol='mV')
                      
#: Unit of concentration - milligrams per liter
mgl = pq.UnitQuantity('Concentration',
                      pq.CompoundUnit("mg/L"),
                      symbol='mg/L')

ugl = pq.UnitQuantity('microgram per liter', mgl / 1000, symbol='ug/L')    
                      
#: Unit of specific conductivity - milliSiemens per centimeter
mScm = pq.UnitQuantity('Specific Conductivity in MilliSiemens per Centimeter',
                       pq.CompoundUnit("1e-3*S/cm"),
                       symbol='mS/cm')

#: Unit of turbidity - nephelometric turbidity units
ntu = pq.UnitQuantity('Turbidity',
                      pq.dimensionless,
                      symbol='NTU')

#: Unit of salinity - practical salinity units
psu = pq.UnitQuantity('Salinity',
                      pq.dimensionless,
                      symbol='PSU')
ppt = psu

# nickname for dimensionless
dl = pq.dimensionless

#unit of speed
mps = pq.UnitQuantity('meter per second', pq.m / pq.second, symbol='m/s')
fps = pq.UnitQuantity('foot per second', pq.foot / pq.second, symbol='ft/s')

#: Unit of specific conductivity - microSiemens per centimeter
uScm = pq.UnitQuantity('Specific Conductivity',
                       pq.CompoundUnit("1e-6*S/cm"),
                       symbol='uS/cm')

#: Units of Depth/Water Surface Elevation - meters/ft of water
mH2O = pq.UnitQuantity('meters of water', pq.m * pq.conventional_water,
                       symbol='mH2O')
ftH2O = pq.ftH2O  # since ftH20 already exists in pq
#: Pressure in dbar
dbar = pq.UnitQuantity('decibar', pq.CompoundUnit('0.1*bar'), symbol='dbar')
#: Pressure in kPa
kPa = pq.pressure.kPa

#units of flow rate
cms  = pq.UnitQuantity('cubic meter per second', pq.meter ** 3 / pq.second, 
                       symbol='cms')
cfs = pq.UnitQuantity('cubic foot per second', pq.foot ** 3 / pq.second,
                      symbol='cfs')
afd = pq.UnitQuantity('acre foot per day', pq.volume.acre_foot / pq.day,
                      symbol='afd')
