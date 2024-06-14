"""
Course-related functionality, including constraints.
"""

from typing import Dict, Union
from abc import ABC, abstractmethod

from common_utils import JsonSer, TIFactory, DEFAULT_TZN
from available import Available, AvailableFactory


ACTIVITY = "activity"
PERIOD_DUR = "periodDuration"
IS_INTENSIVE = "intensiveCourse"
DURATION = "duration"
PERIODS = "periods"
DATES = "dates"
DETAILS = "advancedDetails"
TIMEZONE = "timeZone"

# For calendar invite
COURSE_NAME = "ssku"
INSTITUTE_NAME = "instituteName"

CLASS_DEF = "classDefinition"


# the min distance between ticks on the grid, such as 10 mins or 30 mins.
# TODO: figure out where to get from, either time data itself or separately based on school.
TICK_DIST = 'tick_dist'


class Activity(JsonSer):
    """Activity within a course."""
    def __init__(self, **kwargs):
        self.name = kwargs.get(ACTIVITY)
        self.periods = kwargs.get(PERIODS, 1)
        self.period_dur = kwargs.get(PERIOD_DUR, 60)
        self.segment_dur = self.periods * self.period_dur
        self.duration = kwargs.get(DURATION, 60)

    @property
    def to_dict(self):
        return {
            ACTIVITY: self.name,
            PERIODS: self.periods,
            DURATION: self.duration,
        }


class Course(JsonSer, ABC):
    """Course-related stuff."""

    avail_factories = {}

    def __init__(self, **kwargs):
        self.name = kwargs.get(COURSE_NAME, 'unknown course name')
        self.period_dur = kwargs.get(PERIOD_DUR, 60)
        self.tick_dist = kwargs.get(TICK_DIST, 30)
        self.tz_name = kwargs.get(TIMEZONE, DEFAULT_TZN)

        self.avail = Available(self.name, self.tz_name)
        tif = TIFactory(self.tz_name)
        for date in kwargs.get(DATES, []):
            self.avail.add_interval(tif.from_tidd(date, ACTIVITY))

        self.activities = []

        for detail in kwargs.get(DETAILS, []):
            detail.update(kwargs)
            self.activities.append(Activity(**detail))

        # For now, assume all activities are of the same duration;
        # TODO: fix scheduling etc.
        self.segment_dur = max([act.segment_dur for act in self.activities])

    @property
    def duration(self) -> int:
        """Total duration of all activities."""
        return sum([act.duration for act in self.activities])

    @property
    def activity_dict(self) -> Dict[str, Activity]:
        """Return activities as a dict."""
        out = {}
        for act in self.activities:
            out[act.name] = act
        return out

    @property
    def to_dict(self):
        return {
            COURSE_NAME: self.name,
            PERIOD_DUR: self.period_dur,
            # TODO: replace with kind of course.
            # IS_INTENSIVE: self.is_intensive,
            DETAILS: [act.to_dict for act in self.activities],
            DATES: self.avail.to_dict[DATES],
            DURATION: self.duration,
        }

    @abstractmethod
    def avail_factory(self) -> callable:
        pass

    @abstractmethod
    def populate_avail(self, avail: Available) -> Available:
        pass


class CourseConvenience(Course):
    """Convenience."""

    def populate_avail(self, avail: Available) -> Available:
        return avail

    def avail_factory(self) -> callable:
        return None


class CourseAdvanced(Course):
    """Advanced course -- fully specified."""

    @property
    def avail_factory(self) -> callable:
        return AvailableFactory.identity

    def populate_avail(self, avail: Available) -> Available:
        """Only one potential schedule."""
        return avail


class CourseIntensive(Course):
    """Intensive course -- needs to be compact."""

    @property
    def avail_factory(self) -> callable:
        return AvailableFactory.random

    def populate_avail(self, avail: Available) -> Available:
        """
        Take an unlabeled availability and populate it with entries.

        Algo:
        TODO: document it
        """
        out = Available(self.avail.name, self.tz_name)
        act_total = {}
        for ti in avail.dts():
            if out.duration >= self.duration:
                break
            filled = {}
            while len(filled) < len(self.activities):
                for act in self.activities:
                    act_total.setdefault(act.name, 0)
                    if act_total[act.name] >= act.duration or act.segment_dur > ti.duration:
                        filled[act.name] = True
                        continue
                    init = TIFactory.initial(ti, act.segment_dur, ACTIVITY, act.name)
                    if init:
                        out.add_interval(init)
                        act_total[act.name] += init.duration
                        ti = TIFactory.reduced(ti, act.segment_dur)
                        if not ti:
                            break
        return out


class CourseRegular(Course):
    """Regular course -- needs to be spread out."""

    @property
    def avail_factory(self) -> callable:
        return AvailableFactory.days_of_week

    def populate_avail(self, avail: Available) -> Union[Available, None]:
        """
        Take an unlabeled availability and populate it with entries.

        Assume days of the week or other regularity has been taken care of.
        What we need is layering: go from the beginning to the end, using the same time slot.
        Once it runs out, use the next time slot.
        """

        # TODO: more randomization; can start with different time slots.
        # TODO: probably the same issue with duration -- needs to take into account segment lengths.

        time_slots = AvailableFactory.common_time_slots(
            avail, self.duration, self.segment_dur, self.tick_dist)
        if not time_slots:
            return None

        out = Available(avail.name, self.tz_name)
        act_total = {}
        for av in time_slots:
            if out.duration > self.duration:
                break
            filled = {}
            # TODO: rewrite the below, since ti's are supposed to match activity lengths.
            for ti in av.dts():
                for act in self.activities:
                    act_total.setdefault(act.name, 0)
                    if act_total[act.name] >= act.duration or act.segment_dur > ti.duration:
                        filled[act.name] = True
                        continue
                    init = TIFactory.initial(ti, act.segment_dur, ACTIVITY, act.name)
                    if init:
                        out.add_interval(init)
                        act_total[act.name] += init.duration
                        ti = TIFactory.reduced(ti, act.segment_dur)
                        if not ti:
                            break
        return out


class CourseFactory:
    """Creation of Course Objects."""

    @staticmethod
    def from_req_dict(rd: dict) -> Course:
        """Return one of three types of courses."""
        rd.update(rd[CLASS_DEF])
        c = CourseFactory._pre_from_req_dict(rd)
        
        # advanced is fully specified
        if c.duration == c.avail.duration:
            return CourseAdvanced(**rd)
        
        # the caller may use the "false" string instead of false
        intensive = rd.get(IS_INTENSIVE, False)
        if isinstance(intensive, str) and intensive.lower() == 'false':
            intensive = False
        
        if intensive:
            return CourseIntensive(**rd)
        
        return CourseRegular(**rd)

    @staticmethod
    def _pre_from_req_dict(rdu: dict) -> Course:
        """Convenience to figure out if the course is advanced or not only."""
        return CourseConvenience(**rdu)
