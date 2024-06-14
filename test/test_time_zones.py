"""
Tests of time zone date conversion functionality.
"""

from common_utils import to_tz_dt
from dateutil.parser import parse as date_parse


class TestTZ:
    tz_ps = 'Europe/Paris'
    tz_la = 'America/Los_Angeles'
    tz_ad = 'Africa/Dakar'
    tz_as = 'Australia/Sydney'

    def test1(self):
        s1 = "2021-07-08T09:00:00"
        dt1 = to_tz_dt(self.tz_ps, s1)
        dt11 = to_tz_dt(self.tz_ps, date_parse(s1))
        assert str(dt1) == '2021-07-08 09:00:00+02:00' == str(dt11)

    def test2(self):
        s2 = "2021-12-08T09:00:00"
        dt2 = to_tz_dt(self.tz_ps, s2)
        dt21 = to_tz_dt(self.tz_ps, date_parse(s2))
        assert str(dt2) == '2021-12-08 09:00:00+01:00' == str(dt21)

    def test3(self):
        s1 = "2021-07-08T09:00:00-05:00"
        dt1 = to_tz_dt(self.tz_ps, s1)
        assert str(dt1) == '2021-07-08 16:00:00+02:00'
        dt2 = to_tz_dt(self.tz_la, dt1)
        assert str(dt2) == '2021-07-08 07:00:00-07:00'

    def test4(self):
        s1 = "2021-07-08T09:30:00-05:00"
        dt1 = to_tz_dt(self.tz_ps, s1, ignore_tz=True)
        assert str(dt1) == '2021-07-08 09:30:00+02:00'
        dt2 = to_tz_dt(self.tz_la, dt1)
        assert str(dt2) == '2021-07-08 00:30:00-07:00'

    def test5(self):
        s1 = "2021-07-08T09:00:00-05:00"
        dt1 = to_tz_dt(self.tz_ad, s1)
        assert str(dt1) == '2021-07-08 14:00:00+00:00'
        dt2 = to_tz_dt(self.tz_la, dt1)
        assert str(dt2) == '2021-07-08 07:00:00-07:00'

    def test6(self):
        s1 = "2021-07-08T11:00:00-05:00"
        dt1 = to_tz_dt(self.tz_as, s1)
        assert str(dt1) == '2021-07-09 02:00:00+10:00'
        dt2 = to_tz_dt(self.tz_la, dt1)
        assert str(dt2) == '2021-07-08 09:00:00-07:00'
