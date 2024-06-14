"""
Test of the tc_event functionality...
"""

from cal_time_zones import get_tz_name
from common_utils import TIFactory
from datetime import timedelta
from icalendar import Event

from tc_event import SEventTentativeFactory, DT_START, DT_END, SUMMARY, DT_STAMP
from tc_event import SEvent


class TestSevent:
    """Tests for server-side events..."""
    fname = 'test/data/lara-edwards-sundays.ics'
    body = open(fname).read()
    e = SEvent(body, '2021-07-07 12:00:00+02:00')

    def test1(self):
        e = self.e
        assert e.tz_name == 'America/New_York'
        assert e.uid == '18ABFE-60DBD700-D-49EC8800'
        assert str(e.dt_start) == '2021-07-04 11:00:00-04:00'
        assert str(e.dt_end) == '2021-07-04 18:00:00-04:00'

    def test2(self):
        """Make sure the number of dates is right..."""
        e = self.e
        assert len(e.dts()) == 4
        assert len(e.dts(start='2021-07-06')) == 3
        assert len(e.dts(end='2021-07-14')) == 2


class TestInvite:

    @staticmethod
    def do_test(tz_name: str):
        tif = TIFactory(tz_name)
        ti = tif.from_se('2021-06-26 10:00:00', '2021-06-26 14:00:00')
        args = {
            DT_START: ti.start,
            DT_END: ti.end,
            DT_STAMP: ti.start - timedelta(days=20),
            SUMMARY: 'A test event',
        }
        event_str = SEventTentativeFactory().get_invite_str(**args)

        ev = Event.from_ical(event_str)
        assert tz_name == get_tz_name(ev)

        # TODO: more info extraction...

        print()
        print("GOT EVENT STR\n")
        print(event_str)
        print()

    def test_invite1(self):
        self.do_test('America/Chicago')

    def test_invite2(self):
        self.do_test('Africa/Dakar')

    def test_invite3(self):
        self.do_test('America/Santiago')

    def test_invite4(self):
        self.do_test('Europe/Zurich')
