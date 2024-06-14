from client_calendar import get_default_scal
from available import AvailableFactory, DATES, NAME
from course import ACTIVITY

import json


class TestCompat:
    email = 'rebecca.young@alvizion.com'
    cal = get_default_scal(email)

    def test1(self):
        """Test compatibility of a teacher with a course."""
        start, end = '2021-07-05', '2021-08-05'
        events = self.cal.get_events(start, end)
        av = AvailableFactory.from_events(self.email, events, start, end)

        dd = json.load(open('test/data/test_schedule/br_mon_fri_intensive_ry.json'))
        aa = AvailableFactory.from_tids('Class Schedule', 'Europe/Paris', dd[DATES], ACTIVITY)

        common = AvailableFactory.intersect(av, aa)
        assert common.duration >= 1000


class TestDiff:
    email = 'rebecca.young@alvizion.com'
    cal = get_default_scal(email)

    def test1(self):
        """Test the split of Sunday invite into two intervals."""
        start, end = '2021-07-12', '2021-08-12'
        events = self.cal.get_events(start, end)
        av = AvailableFactory.from_events(self.email, events, start, end)
        dd = av.to_dict
        sun_cnt, mwf_cnt, tue_cnt = 0, 0, 0
        for elt in dd[DATES]:
            sun_cnt += 1 if 'Sun' in elt[NAME] else 0
            tue_cnt += 1 if 'Tue' in elt[NAME] else 0
            mwf_cnt += 1 if 'MWF' in elt[NAME] else 0

        # Sunday was split into two; so the total numbers should roughly be these.
        assert sun_cnt > 0.5 * mwf_cnt
        assert sun_cnt > 0.75 * tue_cnt

    def test2(self):
        """More refined test -- take 2 Sundays."""
        start = '2021-07-18'
        end = '2021-07-26'
        events = self.cal.get_events(start, start)
        sun_evs = [ev for ev in events if 'Sun' in ev.summary]
        busy_evs = [ev for ev in events if '**' in ev.summary]
        sun_av = AvailableFactory.from_events(self.email, sun_evs, start, end)
        busy_av = AvailableFactory.from_events(self.email, busy_evs, start, end)
        all_av = AvailableFactory.from_events(self.email, sun_evs + busy_evs, start, end)
        assert sun_av.duration == 240*2
        assert busy_av.duration == 0
        assert all_av.duration == 90*2
