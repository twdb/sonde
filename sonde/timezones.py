"""
    sonde.timezones
    ~~~~~~~~~~~~~~~~

    This module contains some convenient tzinfo handling methods
"""
from datetime import timedelta

from pytz.tzinfo import StaticTzInfo


class UTCStaticOffset(StaticTzInfo):
    def __init__(self, offset):
        if not isinstance(offset, int):
            raise ValueError("Offset must be an integer value")

        self._utcoffset = timedelta(hours=1) * offset
        sign = "+" if offset > 0 else ""
        self._tzname = "UTC" + sign + str(offset)
        self.zone = self._tzname


cst = UTCStaticOffset(-6)
cdt = UTCStaticOffset(-5)
