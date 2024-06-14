"""
Tests for the optimal events functionality.
"""

# from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY

from available import AvailableFactory
from opt_events import TIRRule


def test1():
    # Optimal: 2 rrules, 1 day of the week, another separate
    tids = [
        {
          "startTime": "2021-07-05T10:00:00",
          "endTime": "2021-07-05T13:00:00"
        },
        {
          "startTime": "2021-07-12T10:00:00",
          "endTime": "2021-07-12T13:00:00"
        },
        {
          "startTime": "2021-07-19T10:00:00",
          "endTime": "2021-07-19T13:00:00"
        },
        {
          "startTime": "2021-07-20T10:00:00",
          "endTime": "2021-07-20T12:00:00"
        }
    ]

    avail = AvailableFactory.from_tids('America/Chicago', 'aa', tids)
    tir = TIRRule(avail.dts())
    tir.compute_optimal_rules()

    assert len(tir.rule_tis) == 2
    print()
    for mrule, _ in tir.rule_tis:
        print(str(mrule))


def test2():
    # Optimal: 3 rrules, presumably
    tids = [
        {
          "activity": "Lecture",
          "startTime": "2021-09-06T13:00:00",
          "endTime": "2021-09-06T15:00:00"
        },
        {
          "activity": "Tutorials",
          "startTime": "2021-09-08T14:00:00",
          "endTime": "2021-09-08T16:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-09-10T14:00:00",
          "endTime": "2021-09-10T16:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-09-13T13:00:00",
          "endTime": "2021-09-13T15:00:00"
        },
        {
          "activity": "Tutorials",
          "startTime": "2021-09-15T14:00:00",
          "endTime": "2021-09-15T16:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-09-17T14:00:00",
          "endTime": "2021-09-17T16:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-09-20T13:00:00",
          "endTime": "2021-09-20T15:00:00"
        },
        {
          "activity": "Tutorials",
          "startTime": "2021-09-22T14:00:00",
          "endTime": "2021-09-22T16:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-09-24T14:00:00",
          "endTime": "2021-09-24T16:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-09-27T13:00:00",
          "endTime": "2021-09-27T15:00:00"
        },
        {
          "activity": "Tutorials",
          "startTime": "2021-09-29T14:00:00",
          "endTime": "2021-09-29T16:00:00"
        },
        {
          "activity": "Exam",
          "startTime": "2021-10-01T10:00:00",
          "endTime": "2021-10-01T12:00:00"
        },
        {
          "activity": "Lecture",
          "startTime": "2021-10-01T14:00:00",
          "endTime": "2021-10-01T16:00:00"
        }
    ]

    avail = AvailableFactory.from_tids('America/Chicago', 'bb', tids)
    tir = TIRRule(avail.dts())
    tir.compute_optimal_rules()

    assert len(tir.rule_tis) == 3

    print()
    for mrule, _ in tir.rule_tis:
        print(mrule)
