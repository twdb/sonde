"""
provides a set of timezones
"""

from pytz.tzinfo import StaticTzInfo
from datetime import timedelta


class UTCStaticOffset(StaticTzInfo):
    def __init__(self, offset):
        if type(offset) != int:
            raise ValueError, "Offset must be an integer value"
        
        self._utcoffset = timedelta(hours=1) * offset
        sign = "+" if offset > 0 else ""
        self._tzname = "UTC"+ sign + str(offset)
        self.zone = self._tzname


cst = UTCStaticOffset(-6)
cdt = UTCStaticOffset(-5)
