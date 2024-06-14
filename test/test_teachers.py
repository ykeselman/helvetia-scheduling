"""
Teachers functionality testing.
"""

from abc import ABC

from teacher import TeacherFactoryRest, TeacherFactoryAvail
from tc_event import SEvent
from glob import glob


class TFTest(ABC):
    factory = None


class TestTFRE(TFTest):
    factory = TeacherFactoryRest()

    def check(self, email: str, flag: bool):
        teacher = self.factory.from_email(email)
        if flag:
            print()
            print(teacher)
            assert teacher
        else:
            assert not teacher

    def test1(self):
        self.check('kristen.bell@teacher.com', True)

    def test2(self):
        self.check('jake.bluuse@gmail.com', True)

    def test3(self):
        self.check('dmarc@alvizion.com', True)

    def test5(self):
        self.check('nobody@nobody.com', False)

    def test7(self):
        self.check('teacher1@alvizion.com', True)

    def test8(self):
        self.check('teacher2@alvizion.com', True)


class TestTFRI(TFTest):
    factory = TeacherFactoryRest()

    def test55y(self):
        tid = 135
        teacher = self.factory.from_id(tid)
        assert teacher

    def test55n(self):
        tid = -135
        teacher = self.factory.from_id(tid)
        assert not teacher


class TestTFA(TFTest):
    factory = TeacherFactoryAvail(glob('test/data/test_schedule/teacher_*'))

    def test1(self):
        teacher = self.factory.from_id(3)
        assert teacher

    def test2(self):
        teacher = self.factory.from_id(4)
        assert teacher


class TestAddRemove:
    factory = TeacherFactoryRest()
    email = 'lara.edwards@alvizion.com'
    teacher = factory.from_email(email)

    def test1(self):
        evb, cevb = (
            open('test/data/lara-edwards-sundays.ics').read(),
            open('test/data/lara-edwards-sundays-cancel.ics').read()
        )

        e = SEvent(evb, '')

        # faulty calendar operations
        # for ev in self.teacher.get_events():
        #     assert ev.uid != e.uid

        self.teacher.handle_event(evb, '')

        was_found = False
        for ev in self.teacher.get_events(e.dt_start, e.dt_end):
            if ev.uid == e.uid:
                was_found = True
        assert was_found

        self.teacher.handle_event(cevb, '')

        for ev in self.teacher.get_events(e.dt_start, e.dt_end):
            assert ev.uid != e.uid
