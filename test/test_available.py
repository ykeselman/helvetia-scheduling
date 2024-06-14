"""
Testing of the Available functionality.
"""

# import json

from course import ACTIVITY
from available import Available, AvailableFactory
from common_utils import TIFactory


class TestBasic:
    tids = [
        {
            "activity": "Lecture",
            "startTime": "2021-07-05T10:00:00",
            "endTime": "2021-07-05T13:00:00"
        },
        {
            "activity": "Lecture",
            "startTime": "2021-07-12T10:00:00",
            "endTime": "2021-07-12T13:00:00"
        },
        {
            "activity": "Lecture",
            "startTime": "2021-07-19T10:00:00",
            "endTime": "2021-07-19T13:00:00"
        },
        {
            "activity": "Exam",
            "startTime": "2021-07-20T10:00:00",
            "endTime": "2021-07-20T12:00:00"
        }
    ]

    aa = AvailableFactory.from_tids('Class Schedule', 'America/Chicago', tids, ACTIVITY)

    def test_start_end(self):
        assert str(self.aa.start) == "2021-07-05 10:00:00-05:00"
        assert str(self.aa.end) == "2021-07-20 12:00:00-05:00"


class TestIntersect:
    # TODO: refactor the tests
    def test1(self):
        """
        Test of intersection of 2 availabilities.
        Dates can be with/without offsets, does not matter due to time zone.
        """

        tz_name = 'America/Chicago'
        aa = Available('aa', tz_name)
        ab = Available('ab', tz_name)
        tif = TIFactory(tz_name)

        ta1 = tif.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00')
        ta2 = tif.from_se('2021-05-20 13:00:00', '2021-05-20 15:00:00')
        ta3 = tif.from_se('2021-05-21 09:00:00', '2021-05-21 15:00:00')
        ta4 = tif.from_se('2021-05-22 07:00:00', '2021-05-22 15:00:00')
        aa.add_intervals([ta1, ta2, ta3, ta4])

        # These will translated into the same time zone
        tb1 = tif.from_se('2021-05-20 09:00:00', '2021-05-20 13:00:00')
        tb2 = tif.from_se('2021-05-20 14:00:00', '2021-05-20 16:00:00')
        tb3 = tif.from_se('2021-05-21 10:00:00', '2021-05-21 16:00:00')
        tb4 = tif.from_se('2021-05-22 08:00:00', '2021-05-22 16:00:00')
        ab.add_intervals([tb1, tb2, tb3, tb4])

        # TODO: more test cases
        aab = AvailableFactory.intersect(aa, ab)
        assert aab.duration == 16 * 60

    def test2(self):
        """
        Test of intersection of 2 availabilities.
        Dates can be with/without offsets, does not matter due to time zone.
        """

        tza_name = 'America/New_York'
        aa = Available('aa', tza_name)
        tifa = TIFactory(tza_name)

        ta1 = tifa.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00')
        ta2 = tifa.from_se('2021-05-20 13:00:00', '2021-05-20 15:00:00')
        ta3 = tifa.from_se('2021-05-21 09:00:00', '2021-05-21 15:00:00')
        ta4 = tifa.from_se('2021-05-22 07:00:00', '2021-05-22 15:00:00')
        aa.add_intervals([ta1, ta2, ta3, ta4])

        tzb_name = 'America/Chicago'
        ab = Available('ab', tzb_name)
        tifb = TIFactory(tzb_name)

        tb1 = tifb.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00')
        tb2 = tifb.from_se('2021-05-20 13:00:00', '2021-05-20 15:00:00')
        tb3 = tifb.from_se('2021-05-21 09:00:00', '2021-05-21 15:00:00')
        tb4 = tifb.from_se('2021-05-22 07:00:00', '2021-05-22 15:00:00')
        ab.add_intervals([tb1, tb2, tb3, tb4])

        # TODO: more test cases
        aab = AvailableFactory.intersect(aa, ab)
        assert aab.duration == 960


class TestSegmDur:
    """Test of fitting segments into availability."""

    tz_name = 'America/Chicago'
    aa = Available('aa', tz_name)
    tif = TIFactory(tz_name)
    aa.add_intervals([
        tif.from_se('2021-05-13 08:00:00', '2021-05-13 11:00:00'),   # 1
        tif.from_se('2021-05-14 09:00:00', '2021-05-14 12:00:00'),   # 2
    ])

    def test1(self):
        assert self.aa.segm_duration(60) == 360

    def test2(self):
        assert self.aa.segm_duration(120) == 240

    def test3(self):
        assert self.aa.segm_duration(180) == 360

    def test4(self):
        assert self.aa.segm_duration(240) == 0


def get_aa() -> Available:
    tz_name = 'America/Chicago'
    aa = Available('aa', tz_name)
    tif = TIFactory(tz_name)
    aa.add_intervals([
        tif.from_se('2021-05-13 08:00:00', '2021-05-13 15:00:00'),   # 1
        tif.from_se('2021-05-14 09:00:00', '2021-05-14 16:00:00'),   # 2
        tif.from_se('2021-05-20 08:00:00', '2021-05-20 15:00:00'),   # 1
        tif.from_se('2021-05-21 09:00:00', '2021-05-21 16:00:00'),   # 2
        tif.from_se('2021-05-27 08:00:00', '2021-05-27 15:00:00'),   # 1
        tif.from_se('2021-05-28 09:00:00', '2021-05-28 16:00:00'),   # 2
    ])
    return aa


class TestDayOfWeek:

    @staticmethod
    def test1():
        aa = get_aa()
        duration = 6 * 3 * 60
        res = AvailableFactory.days_of_week(aa, duration, 2*60)
        # will fit either into the first set or the second set.
        assert len(res.dts()) == 3
        assert res.duration >= duration
        ti1, ti2, ti3 = res.dts()
        assert ti1.start.weekday() == ti2.start.weekday() == ti3.start.weekday()

    @staticmethod
    def test2():
        aa = get_aa()
        duration = 10 * 3 * 60
        res = AvailableFactory.days_of_week(aa, duration, 2*60)
        # will not fit either into the first set or the second set; need both
        assert len(res.dts()) == 6
        assert res.duration >= duration


class TestSlots:

    @staticmethod
    def test1():
        aa = get_aa()
        slot_dur = 120
        duration = 3 * slot_dur
        tick_dur = 15
        dow = AvailableFactory.days_of_week(aa, duration, slot_dur)
        res = AvailableFactory.common_time_slots(dow, duration, slot_dur, tick_dur)
        assert len(res) == 1
        assert len(res[0].dts()) == 3
        # print("GOT RES")
        # print(json.dumps(res.to_dict, indent=2))

    @staticmethod
    def test2():
        aa = get_aa()
        slot_dur = 120
        duration = 6 * slot_dur
        tick_dur = 15
        dow = AvailableFactory.days_of_week(aa, duration, slot_dur)
        res = AvailableFactory.common_time_slots(dow, duration, slot_dur, tick_dur)
        assert len(res) == 2
        assert len(res[0].dts()) == 3
        assert len(res[1].dts()) == 3
        # print("GOT RES")
        # print(json.dumps(res.to_dict, indent=2))


class TestGrid:
    # TODO: more tests

    def test_grid(self):
        """Make sure the grid is the right kinds."""
        aa = get_aa()
        period, tick = 120, 15
        grid = aa.day_grid(period, tick)
        dates = set()
        for i, ti in enumerate(grid):
            assert ti.duration == period
            if i > 0:
                assert (ti.start - grid[i-1].start).seconds == tick*60
            dates.add(ti.start.date())
        assert len(dates) == 1

        aa_min_hour = min([ti.start.hour for ti in aa.dts()])
        aa_max_hour = max([ti.end.hour for ti in aa.dts()])
        gr_min_hour = min([ti.start.hour for ti in grid])
        gr_max_hour = max([ti.end.hour for ti in grid])
        assert aa_min_hour == gr_min_hour
        # TODO: not all time intervals are covered
        # TODO: investigate...
        assert aa_max_hour == gr_max_hour
        # print(json.dumps(grid.to_dict, indent=2))


class TestCompact:
    # TODO: more tests
    def test_compact(self):
        tz_name = 'America/Chicago'
        aa = Available('aa', tz_name)
        tif = TIFactory(tz_name)
        aa.add_intervals([
            tif.from_se('2021-05-13 08:00:00', '2021-05-13 11:00:00'),   # 1a
            tif.from_se('2021-05-13 11:00:00', '2021-05-13 15:00:00'),   # 1b
            tif.from_se('2021-05-13 15:00:00', '2021-05-13 17:00:00'),   # 1c
            tif.from_se('2021-05-20 09:00:00', '2021-05-20 12:00:00'),   # 2a
            tif.from_se('2021-05-20 12:00:00', '2021-05-20 15:00:00'),   # 2b
            tif.from_se('2021-05-20 15:00:00', '2021-05-20 18:00:00'),   # 2c
        ])

        aac = AvailableFactory.compacted(aa)
        tis = aac.dts()
        assert len(tis) == 2
        assert tis[0].duration == 9*60
        assert tis[1].duration == 9*60


class TestDiff:

    def test1(self):
        tz_name = 'America/Chicago'
        aa = Available('aa', tz_name)
        tif = TIFactory(tz_name)

        pos_ints = [
            tif.from_se('2021-05-13 08:00:00', '2021-05-13 11:00:00'),   # 1a
            tif.from_se('2021-05-13 11:00:00', '2021-05-13 15:00:00'),   # 1b
            tif.from_se('2021-05-13 15:00:00', '2021-05-13 17:00:00'),   # 1c
            tif.from_se('2021-05-20 09:00:00', '2021-05-20 12:00:00'),   # 2a
        ]
        aa.add_intervals(pos_ints)

        neg_ints = [
            tif.from_se('2021-05-13 09:00:00', '2021-05-13 10:00:00'),  # 1a
            tif.from_se('2021-05-13 11:00:00', '2021-05-13 15:00:00'),  # 1b
            tif.from_se('2021-05-13 15:00:00', '2021-05-13 16:00:00'),  # 1c
            tif.from_se('2021-05-20 11:00:00', '2021-05-20 12:00:00'),  # 2a
        ]
        aa.add_neg_intervals(neg_ints)

        assert aa.duration == sum([ti.duration for ti in pos_ints]) - sum([ti.duration for ti in neg_ints])

        # The first interval split into two, the second removed, the third and forth 1 piece each.
        assert len(aa.dts()) == 4
