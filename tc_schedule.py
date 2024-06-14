"""
A schedule class that combines conditions/avails from course, instructors.
"""

# import json

from typing import List, Union

from course import Course
from teacher import Teacher
from available import Available, AvailableFactory, SUMMARY, DESCRIPTION
from tc_schedule_rating import ScheduleRating

N_CANDIDATES = 'n_candidates'
N_CANDIDATES_DEFAULT = 10

RANKING_STRAT = 'ranking_strat'
RANKING_STRAT_EARLIEST = 'earliest'


class Scheduler:
    """Brings together instructor and schedule."""

    # If no schedules found, reduce the multiplier
    # The last one is for fully-specified courses...
    CDUR_MULT = [1.3, 1.2, 1.1, 1.0]

    def __init__(self, course: Course, teacher: Teacher, intersect: Available, **kwargs):
        """A scheduler instance; don't instantiate it directly; use the factory."""
        self.course = course
        self.teacher = teacher
        self.cta = intersect
        self.n_candidates = kwargs.get(N_CANDIDATES, N_CANDIDATES_DEFAULT)
        self.ranking_strat = kwargs.get(RANKING_STRAT, RANKING_STRAT_EARLIEST)

    def schedules(self, n: int) -> List[Available]:
        """Returns schedule candidates."""
        # TODO: better names for time intervals, invites.

        sr = ScheduleRating(self.course, self.teacher)
        c = self.course
        cta = self.cta

        n_cands = max(self.n_candidates, n)

        # Use the factory to implement a specific strategy, such as random.
        out = {}
        for cdur_mult in n_cands * self.CDUR_MULT:
            if len(out) >= n_cands:
                break
            cdur = int(c.duration * cdur_mult)
            avail = c.avail_factory(cta, cdur, c.segment_dur)
            if avail and avail.start not in out:
                cand = c.populate_avail(avail)
                if cand and sr.is_course_feasible(cand) and sr.is_teacher_feasible(cand):
                    out[avail.start] = cand

        # Re-rank the items based on the ranking strategy
        ritems = list(out.items())
        if self.ranking_strat == RANKING_STRAT_EARLIEST:
            ritems = sorted(ritems, key=lambda x: x[0])
        ritems = list(map(lambda x: x[1], ritems[:n]))

        # Add the invites
        for cand in ritems:
            cc = AvailableFactory.compacted(cand)
            cand.set_invites(cc.get_invites(**{
                SUMMARY: c.name,
                DESCRIPTION: c.name
            }))

        return ritems


class SchedulerFactory:
    """Produces scheduler objects."""

    @staticmethod
    def get(course: Course, teacher: Teacher) -> Union[Scheduler, None]:
        """Puts together a scheduler object."""
        if course is None or teacher is None:
            return None

        cavail = course.avail
        if cavail is None:
            return None

        tavail = teacher.get_avail(cavail.start, cavail.end)
        if tavail is None:
            return None

        # print()
        # print(json.dumps(tavail().to_dict, indent=2))
        # print()

        intersect = AvailableFactory.intersect(cavail, tavail)
        if intersect.duration < course.duration:
            return None

        return Scheduler(course, teacher, intersect)
