"""
Days and times available from calendar entries etc.
"""

from typing import List, Dict, Union
import numpy as np
from random import shuffle
from datetime import datetime, timedelta
# from dateutil.parser import parse as date_parse
from intervaltree import IntervalTree

from tc_event import SEvent, DT_STAMP, DT_START, DT_END, SUMMARY, RRULE, UNTIL, DESCRIPTION, \
    SEventCancelFactory, SEventTentativeFactory  # , SEventAccept
from common_utils import TimeInterval, JsonSer, DATES, NAME, TIFactory, DEFAULT_TZN, utc_normalize
from opt_events import TIRRule


CAL_INVITES = 'invites'

REQUEST = 'request'
CANCEL = 'cancel'
REFRESH = 'refresh'


# TODO: initialize differently
# np.random.seed(33)


class Available(JsonSer):
    """Availability for one person or course..."""
    # Note: sets valid/invalid flag for speed; not thread-safe.

    def __init__(self, name: str, tz_name: str):
        self.name = name
        self.tif = TIFactory(tz_name)
        self._events: Dict[str, List[SEvent]] = {}
        self._intervals: List[TimeInterval] = []
        # positive tree (available)
        self._ptree: IntervalTree = IntervalTree()
        # negative tree (busy/unavailable)
        self._ntree: IntervalTree = IntervalTree()
        self._invites: List[Dict[str, str]] = []
        self._dts_valid = True

    @property
    def tz_name(self) -> str:
        return self.tif.tz_name

    @property
    def duration(self) -> int:
        """Return duration in minutes."""
        return sum([ti.duration for ti in self.dts()])

    def segm_duration(self, segm_dur: int) -> int:
        """Return duration in minutes that accommodates the segment duration wholly."""
        return sum([(ti.duration // segm_dur)*segm_dur for ti in self.dts()])

    @property
    def start(self) -> Union[datetime, None]:
        """Return the first time point."""
        ts = self.dts()
        return ts[0].start if ts else None

    @property
    def end(self) -> Union[datetime, None]:
        """Return the last time point."""
        ts = self.dts()
        return ts[-1].end if ts else None

    def add_events(self, events: List[SEvent]):
        """Add a list of Events or their cancellation."""
        for event in events:
            self.add_event(event)

    def add_event(self, event: SEvent):
        """Add an event or its cancellation."""
        uid = event.uid
        self._events.setdefault(uid, []).append(event)
        self._dts_valid = False

    def from_events(self, start: Union[datetime, str], end: Union[datetime, str]) -> List[TimeInterval]:
        """The result of adding positive and negative events."""
        for key, vals in self._events.items():
            last_val: SEvent = sorted(vals, key=lambda x: x.last_modified)[-1]
            if last_val.is_active:
                dts = last_val.dts(start, end)
                if last_val.is_busy:
                    self.add_neg_intervals(dts)
                else:
                    self.add_intervals(dts)
        self.diff_pos_neg()
        self._intervals = list(self._ptree)
        self._intervals.sort()
        self._dts_valid = True
        return self._intervals

    def add_intervals(self, tis: List[TimeInterval]):
        """Add more intervals..."""
        for ti in tis:
            self.add_interval(ti)

    def add_interval(self, ti: TimeInterval):
        """Make sure the intervals are non-overlapping."""
        # TODO: better strategy for overlapping intervals...
        ti = self.tif.from_interval(ti)
        if not self._ptree.overlaps(ti.begin, ti.end):
            self._ptree.add(ti)
            self._dts_valid = False

    def add_neg_intervals(self, tis: List[TimeInterval]):
        """Add more neg intervals..."""
        for ti in tis:
            self.add_neg_interval(ti)

    def add_neg_interval(self, ti: TimeInterval):
        """Add neg interval. Don't check for overlaps, for now..."""
        ti = self.tif.from_interval(ti)
        self._ntree.add(ti)
        self._dts_valid = False

    def dts(self) -> List[TimeInterval]:
        """Returns a list of availability TimeInterval's."""
        if self._dts_valid:
            return self._intervals
        if self._events:
            return self.from_events('2010-10-10', '3003-03-03')
        self.diff_pos_neg()
        self._intervals = list(self._ptree)
        self._intervals.sort()
        self._dts_valid = True
        return self._intervals

    def day_grid(self, slot_dur: int, tick_dur: int) -> List[TimeInterval]:
        """Partition into a grid based on slot size, tick size."""
        dtis = []   # will contain a single date but all time stamps.
        dts = self.dts()
        if not dts:
            return []

        dtss = len(dts) * [dts[0]]
        for ti, tio in zip(dtss, dts):
            dt_start, dt_end = ti.start, ti.end
            dt_start = dt_start.replace(hour=tio.start.hour, minute=tio.start.minute, second=0, microsecond=0)
            dt_end = dt_end.replace(hour=tio.end.hour, minute=tio.end.minute, second=0, microsecond=0)
            dtis.append(TimeInterval(dt_start, dt_end))

        min_ts, max_ts = min(dtis), max(dtis)
        start = min_ts.start.replace(minute=0)
        ts = start

        out = []
        while ts + timedelta(minutes=slot_dur) <= max_ts.end:
            dt_start = ts
            dt_end = ts + timedelta(minutes=slot_dur)
            out.append(TimeInterval(dt_start, dt_end))
            ts += timedelta(minutes=tick_dur)

        return out

    @property
    def to_dict(self) -> dict:
        return {
            NAME: self.name,
            # convert the interval to the target TZ, just in case...
            # DATES: [tif.from_interval(ti).to_dict for ti in self.dts()],
            DATES: [ti.to_dict for ti in self.dts()],
            CAL_INVITES: [invite[REQUEST] for invite in self._invites],
        }

    def __str__(self):
        out = ['AVAIL FOR: ' + str(self.name)]
        out.extend([str(elt) for elt in self.dts()])
        return '\n'.join(out)

    @staticmethod
    def parse_rrule(rrs: str) -> dict:
        # TODO figure out a better way of converting rrules to event dict.
        out = {}
        s = rrs.split(':')[1]
        arr = s.split(';')
        for elt in arr:
            key, val = elt.split('=')
            key = key.upper()
            if ',' in val:
                val = val.split(',')
            out[key] = val
        return out

    def diff_pos_neg(self):
        """Returns the difference between the positive and the negative intervals."""
        pos = self._ptree
        for ni in self._ntree:
            overlap = pos.overlap(ni.begin, ni.end)
            if overlap:
                for ti in overlap:
                    pos.remove(ti)
                    for tii in TIFactory.diff(ti, ni):
                        pos.add(tii)

    def set_invites(self, invites: List[Dict[str, str]]):
        self._invites = invites

    def get_invites(self, **kwargs) -> List[Dict[str, str]]:
        """Generate a list of request and cancel events based on an optimal scheme."""
        # TODO: figure out a better mechanism...
        if not kwargs.get(REFRESH) and self._invites:
            return self._invites

        tentative = SEventTentativeFactory()
        cancel = SEventCancelFactory()

        tir = TIRRule(self.dts())
        tir.compute_optimal_rules()
        for mrule, tis in tir.rule_tis:
            prule = self.parse_rrule(str(mrule).split('\n')[1])
            if UNTIL in prule:
                # need UTC as otherwise the last occurrence can get thrown away.
                prule[UNTIL] = utc_normalize(tis[-1].end)
            kwargs.update({
                RRULE: prule,
                DT_STAMP: utc_normalize(tis[0].start - timedelta(days=1)),
                DT_START: tis[0].start,
                DT_END: tis[0].end,
            })
            name = TIRRule.common_title(tis)
            if not name:
                name = self.name
            if SUMMARY not in kwargs:
                kwargs[SUMMARY] = name
            if DESCRIPTION not in kwargs:
                kwargs[DESCRIPTION] = name
            self._invites.append({
                REQUEST: tentative.get_invite_str(**kwargs),
                CANCEL: cancel.get_invite_str(**kwargs),
            })
        return self._invites


class AvailableFactory:

    # TODO: need a lot more tests...

    @staticmethod
    def compacted(av: Available) -> Available:
        """Compact entries within single days to produce fewer intervals."""
        by_date = {}
        for ti in av.dts():
            date = ti.start.date()
            by_date.setdefault(date, []).append(ti)
        for date in by_date.keys():
            if len(by_date[date]) > 1:
                by_date[date] = TIFactory.merged_list(by_date[date])

        out = Available(av.name, av.tz_name)
        for date in sorted(by_date.keys()):
            out.add_intervals(by_date[date])

        return out

    @staticmethod
    def intersect(a1: Available, a2: Available) -> Available:
        """Returns the intersection of the two."""
        # TODO: better algorithm
        av = Available(a1.name, a1.tz_name)
        for t1 in a1.dts():
            for t2 in a2.dts():
                t12 = TIFactory.intersect(t1, t2)
                if t12:
                    av.add_interval(t12)
        return av

    @staticmethod
    def from_tids(name: str, tz_name: str, tids: List[dict], kw='') -> Available:
        """From requests or mock data."""
        avail = Available(name, tz_name)
        tif = TIFactory(tz_name)
        for elt in tids:
            avail.add_interval(tif.from_tidd(elt, kw))
        return avail

    @staticmethod
    def from_invites(
            name: str, invites: List[str],
            start: Union[datetime, str], end: Union[datetime, str]) -> Available:
        """From a list of invites. Used in testing."""
        events = [SEvent(invite, name) for invite in invites]
        return AvailableFactory.from_events(name, events, start, end)

    @staticmethod
    def from_events(
            name: str, events: List[SEvent],
            start: Union[datetime, str], end: Union[datetime, str]) -> Available:
        """From a list of events."""
        # TODO: figure out if we need the second avail...
        if len(events) > 0:
            tz_name = events[0].tz_name
            avail = Available(name, tz_name)
            avail.add_events(events)
            out = Available(name, tz_name)
            out.add_intervals(avail.from_events(start, end))
            return out
        return Available(name, DEFAULT_TZN)

    @staticmethod
    def from_idx(a: Available, istart=0, iend=-1) -> Available:
        """Produces Available that's a subset of this one."""
        tis = a.dts()
        if iend < 0:
            iend = len(tis)
        out = Available(a.name, a.tz_name)
        out.add_intervals(tis[istart:iend])
        return out

    # TODO: some resulting avails don't jive with segment durations
    # May need a finer way to measure if the avail accommodates that
    # many minutes. Although it's also done at a later stage...

    @staticmethod
    def identity(av: Available, minutes: int, segm_dur: int) -> Union[Available, None]:
        """Return the same as given, assuming it fits."""
        if av.segm_duration(segm_dur) < minutes:
            return None
        return av

    @staticmethod
    def random(av: Available, minutes: int, segm_dur: int) -> Union[Available, None]:
        """A random interval with at least that many minutes."""
        if av.segm_duration(segm_dur) < minutes:
            return None
        upper = len(av.dts())
        istart = int(np.random.uniform(0, upper))
        avr = AvailableFactory.from_idx(av, istart)
        while avr.segm_duration(segm_dur) < minutes:
            istart = int(np.random.uniform(0, upper))
            avr = AvailableFactory.from_idx(av, istart)
        return avr

    @staticmethod
    def days_of_week(av: Available, minutes: int, segm_dur: int) -> Union[Available, None]:
        """
        Outputs an Available that uses as few days of the week as possible.
        Due to randomness, outputs different days of the week.
        """

        by_dow = {}
        for ti in av.dts():
            dow = ti.start.weekday()
            by_dow.setdefault(dow, Available(av.name, av.tz_name))
            by_dow[dow].add_interval(ti)

        dow_avs = sorted(by_dow.items(), key=lambda dav: dav[1].duration, reverse=True)
        shuffle(dow_avs)

        out = Available(av.name, av.tz_name)
        for _, avv in dow_avs:
            out.add_intervals(avv.dts())
            if out.segm_duration(segm_dur) >= minutes:
                return out

    @staticmethod
    def common_time_slots(av: Available, minutes: int, slot_dur: int, tick_dur: int) -> List[Available]:
        """
        Figure out if there are time slots that work across the intervals.
        slot_dur is in minutes, will come from course constraints.

        TODO: better generation based on slot_dur...

        Returns a list of Availables, ready to use in scheduling.
        """
        common: Dict[tuple, Available] = {}
        grid = av.day_grid(slot_dur, tick_dur)
        for ti in grid:
            hh, mm = ti.start.hour, ti.start.minute
            key = (hh, mm)
            for tia in av.dts():
                tise = TIFactory.updated(tia, ti)
                tii = TIFactory.intersect(tia, tise)
                if tii and tii.duration == slot_dur:
                    common.setdefault(key, Available(f'{hh}:{mm}', av.tz_name))
                    common[key].add_interval(tii)

        total_slot_mins: List[tuple, Available]
        total_slot_mins = sorted(common.items(), key=lambda hav: hav[1].duration, reverse=True)

        out: List[Available] = []
        duration = 0
        for hh_mm, avail in total_slot_mins:
            if duration >= minutes:
                break
            to_add = True
            for aprev in out:
                if AvailableFactory.intersect(avail, aprev).duration > 0:
                    to_add = False
                    break
            if to_add:
                out.append(avail)
                duration += avail.duration

        if duration < minutes:
            return []

        return out
