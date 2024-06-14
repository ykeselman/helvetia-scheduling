"""
Testing various schedule-related aspects.
"""

import pandas as pd
import json

from course import CourseFactory
from teacher import TeacherFactoryAvail
from tc_schedule import SchedulerFactory
from tc_schedule_rating import ScheduleRating
from available import CAL_INVITES
from common_utils import DEFAULT_TZN


course_files = [
    'test/data/test_schedule/br_advanced_schedule_4_week_mwf.json',
    'test/data/test_schedule/br_advanced_schedule_intensive_mon.json',
    'test/data/test_schedule/br_advanced_schedule_specific_3_day.json',
    'test/data/test_schedule/br_regular_scheduling_1_month_intense.json',
    'test/data/test_schedule/br_regular_scheduling_3.json',
    'test/data/test_schedule/br_regular_scheduling_5.json',
    'test/data/test_schedule/br_regular_scheduling_6.json',
    'test/data/test_schedule/br_regular_scheduling_mon_fri_2_months.json',
    'test/data/test_schedule/br_regular_scheduling_mwf.json',
    'test/data/test_schedule/br_regular_scheduling_only_never_in.json',
    'test/data/test_schedule/br_regular_scheduling_short_mon_fri.json',
]

teacher_files = [
    'test/data/test_schedule/teacher_availability_derek_jackson.json',
    'test/data/test_schedule/teacher_availability_funkmaster_flex.json',
    'test/data/test_schedule/teacher_availability_janet_smith.json',
    'test/data/test_schedule/teacher_availability_john_wick.json',
    'test/data/test_schedule/teacher_availability_mark_coleman.json',
    'test/data/test_schedule/teacher_availability_never_in.json',
    'test/data/test_schedule/teacher_availability_mark_twain.json',
    'test/data/test_schedule/teacher_availability_rebecca_young.json',
]

TEACHERS = TeacherFactoryAvail(teacher_files)


def test1():
    """Basic tests of compatibility..."""
    print()
    fdf = []
    for cf in course_files:
        cname = cf.split('/')[-1]
        course = CourseFactory.from_req_dict(json.load(open(cf)))
        is_compat = False
        for tid in TEACHERS.ids:
            teacher = TEACHERS.from_id(tid)
            sch = SchedulerFactory.get(course, teacher)
            if sch:
                is_compat = True
                fdf.append({'course': cname, 'email': teacher.email})
        if not is_compat:
            fdf.append({'course': cname, 'email': 'Incompatible with all teachers'})
    print(pd.DataFrame(fdf))


TEACHER = 'teacher'
NMIN = 'nmin'
TZ_NAME = 'tz_name'


class SchedTesting:
    max_reqd_scheds = 3
    max_ret_scheds = 3

    def sched_test(self, cf: str, **kwargs):
        """Test schedules produced from the files..."""

        if TEACHER in kwargs:
            tids = [kwargs[TEACHER]]
        else:
            tids = TEACHERS.ids

        nmin = kwargs.get(NMIN, 0)

        print()
        course = CourseFactory.from_req_dict(json.load(open(cf)))
        for tid in tids:
            teacher = TEACHERS.from_id(tid)
            sr = ScheduleRating(course, teacher)
            sch = SchedulerFactory.get(course, teacher)

            if nmin:
                assert sch

            if sch:
                scheds = sch.schedules(self.max_reqd_scheds)
                assert len(scheds) <= self.max_ret_scheds
                if nmin:
                    assert len(scheds) >= nmin
                print(f"Course {cf.split('/')[-1]} Teacher {teacher.id} Schedules {len(scheds)}")

                for sched in scheds:
                    if TZ_NAME in kwargs:
                        assert sched.tz_name == kwargs[TZ_NAME]
                        # TODO: make sure the intervals agree
                    dd = sched.to_dict
                    print(json.dumps(dd, indent=2))
                    for invite in dd[CAL_INVITES]:
                        assert course.name in invite
                        print(40*'-')
                        print(invite)
                        print(40 * '-')

                        if TZ_NAME in kwargs:
                            arr = invite.split('\n')
                            cnt = sum([1 for elt in arr if kwargs[TZ_NAME] in elt])
                            assert cnt >= 3

                    sr.is_teacher_feasible_assert(sched)
                    sr.is_course_feasible_assert(sched)


class TestAdvanced(SchedTesting):
    max_ret_scheds = 1

    def test1(self):
        self.sched_test('test/data/test_schedule/br_advanced_schedule_4_week_mwf.json')

    def test2(self):
        self.sched_test('test/data/test_schedule/br_advanced_schedule_intensive_mon.json')

    def test3(self):
        self.sched_test('test/data/test_schedule/br_advanced_schedule_specific_3_day.json')

    def test4(self):
        self.sched_test('test/data/test_schedule/br_advanced_schedule_9_week_mf_ry.json')


class TestIntensive(SchedTesting):

    def test11(self):
        self.sched_test(
            'test/data/test_schedule/br_regular_scheduling_short_mon_fri.json',
            **{TEACHER: 3, NMIN: 3, TZ_NAME: 'America/Chicago'}
        )

    def test21(self):
        self.sched_test(
            'test/data/test_schedule/br_mon_fri_intensive_ry_ny.json',
            **{TEACHER: 99449, NMIN: 3, TZ_NAME: 'America/New_York'}
        )

    def test22(self):
        self.sched_test(
            'test/data/test_schedule/br_mon_fri_intensive_ry.json',
            **{TEACHER: 99449, NMIN: 3, TZ_NAME: DEFAULT_TZN}
        )

    def test3(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_1_month_intense.json')

    def test4(self):
        self.sched_test('test/data/test_schedule/br_advanced_schedule_4_week_mwf.json')

    def test5(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_3.json')

    def test6(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_5.json')

    def test7(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_6.json')

    def test8(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_only_never_in.json')


class TestRegular(SchedTesting):

    def test1(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_mwf.json')

    def test2(self):
        self.sched_test('test/data/test_schedule/br_regular_scheduling_mon_fri_2_months.json')


class TestInvites:
    """Test generated invites, compacted."""

    @staticmethod
    def run_test(cfile: str, tid: int, inv_cnts: dict, n=3):
        course = CourseFactory.from_req_dict(json.load(open(cfile)))
        teacher = TEACHERS.from_id(tid)
        sch = SchedulerFactory.get(course, teacher)
        if not sch:
            return
        scheds = sch.schedules(n)
        for idx, nmin in inv_cnts.items():
            sched = scheds[idx]
            assert len(sched.get_invites()) == nmin

    def test1(self):
        cfile = 'test/data/test_schedule/br_regular_scheduling_short_mon_fri.json'
        self.run_test(cfile, 6, {0: 2})

    def test3(self):
        cfile = 'test/data/test_schedule/br_regular_scheduling_short_mon_fri.json'
        self.run_test(cfile, 3, {0: 2})
