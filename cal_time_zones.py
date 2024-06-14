"""
Time zone related ops, including conversion, calendar invites, etc.
"""

from typing import List, Dict
from functools import lru_cache
from icalendar import Calendar, Timezone, TimezoneStandard, TimezoneDaylight, vDDDTypes
from datetime import datetime, timedelta
from dateutil.parser import parse as date_parse
import pytz

from common_utils import DEFAULT_TZN

TZID = 'TZID'
TZ_NAME = 'TZNAME'
DT_START = 'DTSTART'
OFFSET_FROM = 'TZOFFSETFROM'
OFFSET_TO = 'TZOFFSETTO'

OFFSET_LARGE = 'offset_large'
OFFSET_SMALL = 'offset_small'
TZN_STANDARD = 'tzn_standard'
TZN_DAYLIGHT = 'tzn_daylight'
STANDARD_START = 'standard_start'
DAYLIGHT_START = 'daylight_start'


def to_ical_dt(dt: datetime) -> str:
    """Strip time zone, etc."""
    return vDDDTypes(dt).to_ical().decode()


class TDate:
    """Transition date -- from daylight to standard or the other way around."""

    def __init__(self, dt: datetime):
        self.dt = dt
        self.offset = str(dt)[-6:]
        self.tzn = dt.tzname()
        self.is_dst = False


class CalTimeZone:
    """Operations having to do with calendaring time zones."""

    start_year = 2021
    end_year = 2037

    def __init__(self, tz_name: str):
        self.tz = pytz.timezone(tz_name)
        self.adates: Dict[str, TDate] = {}
        self.cdates: List[TDate] = []
        self.offset_small = ''
        self.offset_large = ''
        self.tzns = ''
        self.tznd = ''
        self.populate_dates()

    def get_params(self, dt: datetime) -> dict:
        out = {TZID: self.tz.zone}
        if len(self.adates) >= 1:
            out.update({
                OFFSET_LARGE: self.offset_large,
                OFFSET_SMALL: self.offset_small,
                TZN_STANDARD: self.tzns,
                STANDARD_START: to_ical_dt(pytz.utc.normalize(date_parse('2010-10-10 10:10:10+00:00'))),
            })
        if self.cdates:
            dates = self.search_dates(dt)
            if dates:
                d1, d2 = dates[:2]
                out.update({
                    TZN_DAYLIGHT: self.tznd,
                    STANDARD_START: to_ical_dt(pytz.utc.normalize(d2.dt if d1.is_dst else d2.dt)),
                    DAYLIGHT_START: to_ical_dt(pytz.utc.normalize(d2.dt if d2.is_dst else d1.dt)),
                })
        return out

    def populate_dates(self):
        """
        Populate the sorted list of standard/daylight savings time.
        Use 4:30 am for dst vs st because the switch happens earlier.
        """
        date_start = date_parse(f'{self.start_year}-01-01')
        date_end = date_parse(f'{self.end_year}-12-31')
        dt = date_start.replace(hour=3, minute=30, second=0, microsecond=0)

        dt_prev = self.tz.localize(dt)
        while dt <= date_end:
            dt_next = self.tz.localize(dt)
            if str(dt_prev)[-6:] != str(dt_next)[-6:]:
                self.cdates.append(TDate(dt_next))
            self.adates[str(dt_prev)[-6:]] = TDate(dt_prev)
            dt = dt + timedelta(days=1)
            dt_prev, dt_next = dt_next, self.tz.localize(dt)

        if self.cdates:
            d1, d2 = self.cdates[0], self.cdates[1]
        else:
            vals = list(self.adates.values())
            d1, d2 = vals[0], vals[0]
            self.tzns = d1.tzn

        offsets = [d1.offset, d2.offset]
        soff = sorted(offsets, key=lambda x: int(x[:3]))

        self.offset_small = soff[0].replace(':', '')
        self.offset_large = soff[1].replace(':', '')

        for date in self.cdates:
            if date.offset == soff[1]:
                date.is_dst = True
                self.tznd = date.tzn
            else:
                self.tzns = date.tzn

    def search_dates(self, dt: datetime) -> List[TDate]:
        """Linear search of dates."""
        try:
            dt = self.tz.localize(dt)
        except ValueError:
            pass
        for d1, d2 in zip(self.cdates[:-1], self.cdates[1:]):
            if d1.dt <= dt < d2.dt:
                return [d1, d2]
        return []

    def get_ical_timezone(self, dt: datetime) -> Timezone:
        """Return Timezone info as an ical object."""
        params = self.get_params(dt)
        itz = Timezone()
        itz[TZID] = params[TZID]

        try:
            st = TimezoneStandard()
            st[DT_START] = params[STANDARD_START]
            st[OFFSET_TO] = params[OFFSET_SMALL]
            st[OFFSET_FROM] = params[OFFSET_LARGE]
            st[TZ_NAME] = params[TZN_STANDARD]
            itz.add_component(st)
        except KeyError:
            pass

        try:
            dst = TimezoneDaylight()
            dst[DT_START] = params[DAYLIGHT_START]
            dst[OFFSET_TO] = params[OFFSET_LARGE]
            dst[OFFSET_FROM] = params[OFFSET_SMALL]
            dst[TZ_NAME] = params[TZN_DAYLIGHT]
            itz.add_component(dst)
        except KeyError:
            pass

        return itz


@lru_cache(maxsize=1024)
def get_cal_tz(tz_name: str) -> CalTimeZone:
    """Get one of the objects above."""
    return CalTimeZone(tz_name)


def get_tz_name(cal: Calendar) -> str:
    """Returns the time zone name for further use."""
    if not isinstance(cal, Calendar):
        return DEFAULT_TZN

    tz_found = None
    for component in cal.subcomponents:
        if isinstance(component, Timezone):
            tz_found = component
            break
    if tz_found:
        if TZID in tz_found:
            return str(tz_found[TZID])

    return DEFAULT_TZN
