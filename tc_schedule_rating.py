"""
Rating of Teacher/Course schedules, including feasibility.
"""

from course import Course, ACTIVITY
from teacher import Teacher
from available import Available, AvailableFactory
from common_utils import Logged, get_trace_str


class ScheduleRating(Logged):
    """Rating schedules..."""

    def __init__(self, course: Course, teacher: Teacher):
        self.course = course
        self.teacher = teacher

    @property
    def log_name(self) -> str:
        return f'{self.course.name}:{self.teacher.log_name}'

    def rating(self, avail: Available) -> int:
        self.info("NOT IMPLEMENTED")
        return 0

    def is_teacher_feasible_assert(self, avail: Available):
        """Generates an assertion failure in case things are not feasible."""
        cavail = AvailableFactory.intersect(avail, self.teacher.avail)
        cdur, sdur = cavail.duration, avail.duration
        assert cdur >= sdur, f"not enough teacher minutes: {cdur} < {sdur}"

    def is_teacher_feasible(self, avail: Available, do_warn=False) -> bool:
        """Make sure that the schedule is feasible w.r.t. the teacher."""
        try:
            self.is_teacher_feasible_assert(avail)
            return True
        except AssertionError as ex:
            if do_warn:
                self.warning(get_trace_str(ex))
            return False

    def is_course_feasible_assert(self, avail: Available):
        """Generates an assertion failure in case things are not feasible."""
        course = self.course
        cavail = AvailableFactory.intersect(course.avail, avail)
        cdur, sdur = cavail.duration, avail.duration
        assert cdur >= course.duration, f"not enough minutes: {cdur} < {sdur} = {course.duration}"

        adict = course.activity_dict
        atotal = {}

        # labels are appropriate
        for ti in avail.dts():
            assert ti.label == ACTIVITY, f"wrong TI label: {ti.label}"
            assert ti.value in adict, f"wrong TI activity: {ti.value}"
            assert ti.duration % course.period_dur == 0, f"wrong TI duration: {ti.duration}"
            atotal.setdefault(ti.value, 0)
            atotal[ti.value] += ti.duration
            act = adict[ti.value]
            act_dur = act.period_dur * act.periods
            assert ti.duration % act_dur == 0, f"wrong TI activity duration: {ti.duration}/{act_dur}"

        # appropriate durations per activity
        for act in course.activities:
            assert act.name in atotal
            assert act.duration == atotal[act.name], f"wrong activity total duration: {act.duration}"

    def is_course_feasible(self, avail: Available, do_warn=False) -> bool:
        """Make sure that the schedule is feasible w.r.t. the course."""

        try:
            self.is_course_feasible_assert(avail)
            return True
        except AssertionError as ex:
            if do_warn:
                self.warning(get_trace_str(ex))
            return False
