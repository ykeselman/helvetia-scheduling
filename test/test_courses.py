"""
Test course object creation, etc.
"""

import json

from course import CourseFactory, DURATION, DETAILS, PERIOD_DUR

PFIX = 'test/data/test_schedule'


def do_test(fname: str):
    dd = json.load(open(fname))
    crs = CourseFactory.from_req_dict(dd)
    ddo = json.loads(json.dumps(crs.to_dict, indent=2))
    assert DETAILS in ddo
    assert DURATION in ddo
    assert ddo[DURATION] > 100
    assert ddo[PERIOD_DUR] == 60


def test2():
    fname = f'{PFIX}/br_advanced_schedule_4_week_mwf.json'
    do_test(fname)


def test6():
    fname = f'{PFIX}/br_regular_scheduling_6.json'
    do_test(fname)
