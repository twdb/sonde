"""
quantities specific to sonde
"""
# absolute_import will make sure that when "import quantities as pq"
# is run, quantities refers to the package on sys.path and it is not a
# reference to this file itself
from __future__ import absolute_import

import quantities as pq


mgl = pq.UnitQuantity('Concentration',
                      pq.CompoundUnit("mg/L"),
                      symbol='mg/L')

mScm = pq.UnitQuantity('Specific Conductivity in MilliSiemens per Centimeter',
                       pq.CompoundUnit("1e-3*S/cm"),
                       symbol='mS/cm')

ntu = pq.UnitQuantity('Turbidity',
                      pq.dimensionless,
                      symbol='NTU')

psu = pq.UnitQuantity('Salinity',
                      pq.dimensionless,
                      symbol='PSU')

uScm = pq.UnitQuantity('Specific Conductivity',
                       pq.CompoundUnit("1e-6*S/cm"),
                       symbol='uS/cm')
