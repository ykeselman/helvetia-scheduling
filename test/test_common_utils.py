"""Testing common utils."""

import json

from common_utils import tagged, TIFactory, formatted_template
from response_messages import CONFIRMED, MESSAGES


class TestTI:
    """Testing time intervals."""

    tif = TIFactory('America/Chicago')

    def test_b1(self):
        """Test of basic time interval functionailty."""
        ti = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00', 'Activity', 'Lesson')
        assert ti.start.year == ti.end.year == 2021
        assert ti.start.month == ti.end.month == 5
        assert (ti.end - ti.start).seconds == 4 * 60 * 60
        out = '{"Activity": "Lesson", "startTime": "2021-05-20T08:00:00-05:00", "endTime": "2021-05-20T12:00:00-05:00"}'
        assert out == json.dumps(ti.to_dict)

    def test_in1(self):
        """Test for initial interval."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00', 'name', 'some-name')
        minutes = 100
        assert t1.duration > minutes
        t1i = TIFactory.initial(t1, minutes)
        t1c = TIFactory.reduced(t1, minutes)
        assert t1i.duration + t1c.duration == t1.duration
        assert t1i.label == t1.label == t1c.label
        assert t1i.value == t1.value == t1c.value

    def test_ix1(self):
        """Test for time interval intersects."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00')
        t2 = self.tif.from_se('2021-05-20 09:00:00', '2021-05-20 15:00:00')
        tc = TIFactory.intersect(t1, t2)
        assert tc.duration == 180

    def test_ix2(self):
        """Test for time interval intersects."""
        tif1 = TIFactory('America/Chicago')
        tif2 = TIFactory('America/Los_Angeles')
        t1 = tif1.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00')
        t2 = tif2.from_se('2021-05-20 09:00:00', '2021-05-20 15:00:00')
        tc = TIFactory.intersect(t1, t2)
        assert tc.duration == 60

    def test_m1(self):
        """Merge lists aligned on the boundary."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 12:00:00')
        t2 = self.tif.from_se('2021-05-20 12:00:00', '2021-05-20 15:00:00')
        tc = TIFactory.union(t1, t2)
        assert tc.duration == 7*60

    def test_m2(self):
        """Merge lists non-aligned on the boundary but intersecting."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 13:00:00')
        t2 = self.tif.from_se('2021-05-20 11:00:00', '2021-05-20 15:00:00')
        tc = TIFactory.union(t1, t2)
        assert tc.duration == 7*60

    def test_m3(self):
        """Merge non-intersecting lists."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 11:00:00')
        t2 = self.tif.from_se('2021-05-20 13:00:00', '2021-05-20 15:00:00')
        tc = TIFactory.union(t1, t2)
        assert not tc

    def test_m4(self):
        """Merge a list of 4 intervals into a list of 2 intervals."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 13:00:00')
        t2 = self.tif.from_se('2021-05-20 11:00:00', '2021-05-20 15:00:00')
        t3 = self.tif.from_se('2021-05-21 08:00:00', '2021-05-21 13:00:00')
        t4 = self.tif.from_se('2021-05-21 11:00:00', '2021-05-21 15:00:00')
        tcl = TIFactory.merged_list([t1, t2, t3, t4])
        assert len(tcl) == 2
        assert tcl[0].duration == tcl[1].duration == 7*60

    def test_d1(self):
        """Difference of intervals -- one piece."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 13:00:00')
        t2 = self.tif.from_se('2021-05-20 11:00:00', '2021-05-20 15:00:00')
        td = TIFactory.diff(t1, t2)
        assert len(td) == 1
        assert td[0].duration == 3*60

    def test_d2(self):
        """Difference of intervals -- two pieces."""
        t1 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 15:00:00')
        t2 = self.tif.from_se('2021-05-20 11:00:00', '2021-05-20 13:00:00')
        td = TIFactory.diff(t1, t2)
        assert len(td) == 2
        assert td[0].duration == 3*60
        assert td[1].duration == 2*60

    def test_d3(self):
        """Difference of intervals -- zero pieces."""
        t1 = self.tif.from_se('2021-05-20 11:00:00', '2021-05-20 13:00:00')
        t2 = self.tif.from_se('2021-05-20 08:00:00', '2021-05-20 15:00:00')
        td = TIFactory.diff(t1, t2)
        assert len(td) == 0


class TestTaggedEntries:
    """Test of extraction of tagged parts."""

    def test1(self):
        dd = MESSAGES
        ddt = tagged(dd, CONFIRMED)
        assert len(ddt) > 0

    def test2(self):
        dd = MESSAGES
        ddt = tagged(dd, 'something')
        assert len(ddt) == 0


class TestFormattedTemplate:

    def test1(self):
        fmt = """
Dear Mr. {last_name}:

We are pleased
to welcome
you.
"""

        kv = {'first_name': 'Karl', 'last_name': 'Robinson'}
        out = """
Dear Mr. Robinson:

We are pleased to welcome you.
""".strip()

        assert out == formatted_template(fmt, kv)
