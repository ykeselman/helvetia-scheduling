"""
Tests of transformations between events and available and back.
"""

from available import AvailableFactory, REQUEST
from tc_event import ORGANIZER, MAKE_BUSY
from course import ACTIVITY

# import json

tids1 = [
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

tids2 = [
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


def av_test(tz_name: str, tids: list, inv_cnt: int):
    aa = AvailableFactory.from_tids('Proposed', tz_name, tids, ACTIVITY)
    invites = aa.get_invites(**{ORGANIZER: 'test-scheduling@helvetiaeducation.ch', MAKE_BUSY: False})
    invites = [invite[REQUEST] for invite in invites]

    assert len(invites) == inv_cnt
    # for invite in invites:
    #     print(40*'-')
    #     print(invite)
    #     print(40*'-')

    bb = AvailableFactory.from_invites('Translated', invites, aa.start, aa.end)

    # print(json.dumps(aa.to_dict, indent=2))
    # print()
    # print(json.dumps(bb.to_dict, indent=2))

    assert len(aa.dts()) == len(bb.dts())
    assert aa.duration == bb.duration

    assert AvailableFactory.intersect(aa, bb).duration == aa.duration


def test11():
    av_test('Europe/Zurich', tids1, 2)


def test12():
    av_test('America/Chicago', tids1, 2)


def test21():
    av_test('America/Los_Angeles', tids2, 3)


def test22():
    av_test('Europe/Paris', tids2, 3)
