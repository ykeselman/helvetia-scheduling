"""
Translate availability into an optimal number of events.

This will serve as a way to evaluate schedules, potentially...

For now, use weekly cadence.
"""

from typing import List, Dict, Tuple
from dateutil.rrule import rrule, WEEKLY  # , DAILY, MONTHLY
from collections import Counter

from common_utils import TimeInterval


class TIRRule:
    """Captures a recurring rule that describes a sequence of time intervals."""

    def __init__(self, tis: List[TimeInterval]):
        self.tis = tis
        self.rule_tis: List[Tuple[rrule, List[TimeInterval]]]
        self.rule_tis = []

    @staticmethod
    def common_title(tis: List[TimeInterval]) -> str:
        """Return a common name for the time intervals."""
        vals = [ti.value for ti in tis if ti.label and ti.value]
        if not vals:
            return ''
        cnt = Counter(vals)
        return cnt.most_common(1)[0][0]

    def se_dow_map(self) -> Dict[tuple, Dict[tuple, List[TimeInterval]]]:
        """Returns map indexed by start/end times, DOW, start/end times."""
        out = {}
        for elt in self.tis:
            dow = elt.start.weekday()
            sh = elt.start.hour
            sm = elt.start.minute
            eh = elt.end.hour
            em = elt.end.minute
            key = (sh, sm, eh, em)
            out.setdefault(key, {})
            out[key].setdefault(dow, []).append(elt)

        # merge keys
        for key, ddow in out.items():
            out[key] = self.merge_dow(ddow)

        return out

    @staticmethod
    def merge_dow(dd: dict) -> dict:
        """Merge days of week entries; returns tuples of days mapped into lists of TI's."""
        lens = [len(val) for val in dd.values()]

        # the super-unlikely case of ...
        if max(lens) - min(lens) > 1:
            return dd

        out = {}
        keys = []
        vals = []
        for k, v in dd.items():
            keys.append(k)
            vals.extend(v)

        out[tuple(keys)] = sorted(vals)
        return out

    def compute_optimal_rules(self):
        """Translates a list of time intervals into an equivalent sequence of R rules."""

        by_se_dow = self.se_dow_map()

        for key, wdd in by_se_dow.items():
            for wdk, elts in wdd.items():
                # TODO: wdk should be list or tuple either way...
                if isinstance(wdk, (list, tuple)) and len(elts) == len(wdk):
                    mrule = rrule(freq=WEEKLY, dtstart=elts[0].start, byweekday=wdk, count=1)
                else:
                    mrule = rrule(freq=WEEKLY, dtstart=elts[0].start, byweekday=wdk, until=elts[-1].end)
                self.rule_tis.append((mrule, elts))
