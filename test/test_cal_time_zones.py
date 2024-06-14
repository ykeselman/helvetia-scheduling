"""
Tesing the functionality of time zone operations on calendar invites.
"""

import icalendar as ical
from dateutil.parser import parse as date_parse

from cal_time_zones import get_tz_name, get_cal_tz


class TestSD:

    @staticmethod
    def two_test(tzn: str, dd: str, sd: str):
        """DST goes first."""
        tzo = get_cal_tz(tzn)
        dt = date_parse('2021-08-08')
        res = tzo.search_dates(dt)
        assert len(res) == 2
        r0, r1 = res
        if not r0.is_dst:
            r0, r1 = r1, r0
        assert str(r0.dt) == dd
        assert r0.is_dst
        assert str(r1.dt) == sd
        assert not r1.is_dst

    def test1(self):
        self.two_test('America/Chicago', '2021-03-14 03:30:00-05:00', '2021-11-07 03:30:00-06:00')

    def test21(self):
        self.two_test('Europe/Zurich', '2021-03-28 03:30:00+02:00', '2021-10-31 03:30:00+01:00')

    def test22(self):
        self.two_test('Europe/Paris', '2021-03-28 03:30:00+02:00', '2021-10-31 03:30:00+01:00')

    def test3(self):
        """DST is later in the year due to south hemisphere"""
        self.two_test('Australia/Sydney', '2021-10-03 03:30:00+11:00', '2021-04-04 03:30:00+10:00')

    def test4(self):
        """DST is later in the year due to south hemisphere"""
        self.two_test('America/Santiago', '2021-09-05 03:30:00-03:00', '2021-04-04 03:30:00-04:00')

    @staticmethod
    def zero_test(tzn: str):
        """No DST."""
        tzo = get_cal_tz(tzn)
        dt = date_parse('2021-08-08')
        res = tzo.search_dates(dt)
        assert len(res) == 0

    def test5(self):
        self.zero_test('Africa/Dakar')

    def test6(self):
        self.zero_test('Africa/Johannesburg')

    def test7(self):
        self.zero_test('America/Sao_Paulo')


# TODO: invites with the above


def test1():
    """First invite."""
    fname = 'test/data/invite-2021-06-03.ics'
    invite = open(fname).read()
    ev = ical.Event.from_ical(invite)
    tz_name = get_tz_name(ev)
    assert tz_name == 'Europe/Zurich'


def test2():
    """Second invite."""
    fname = 'test/data/invite-2021-03-03.ics'
    invite = open(fname).read()
    ev = ical.Event.from_ical(invite)
    tz_name = get_tz_name(ev)
    assert tz_name == 'America/New_York'


def no_test_t2():
    tzo = get_cal_tz('America/Chicago')
    print()
    for date in tzo.cdates:
        print(date.dt, date.offset, date.is_dst)
    print()
    # print(tzo.tz_invite(parse('2021-06-25 10:00:00')))
