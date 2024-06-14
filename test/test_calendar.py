"""
Testing calendar functionality -- it won't be much used, probably...
"""

from client_calendar import get_default_scal, SEvent


def test_cal_get_events():
    """Read events from the calendar."""
    cal_name = 'cal-test-dont-delete'
    cal = get_default_scal(cal_name)
    events = cal.get_events('2021-08-08', '2022-08-08')
    assert len(events) > 0
    cal.info(f"TOTAL EVENTS FOUND: {len(events)}")
    for event in events:
        assert isinstance(event, SEvent)
        cal.info(event.body)
        print()
        print(event)
        print()


def test_add_remove_event():
    """Test addition and removal of events."""
    fname = 'test/data/lara-edwards-sundays.ics'
    body = open(fname).read()
    e = SEvent(body, '2021-07-07 12:00:00+02:00')

    scal = get_default_scal('cal-test-dont-delete')

    # faulty calendar operations
    # for ev in scal.get_events():
    #     assert ev.uid != e.uid

    scal.add_event(body, '2021-06-06 12:00:00-02:00')

    was_found = False
    for ev in scal.get_events(e.dt_start, e.dt_end):
        if ev.uid == e.uid:
            was_found = True
    assert was_found

    scal.delete_event(e.uid, e.dt_start, e.dt_end)

    for ev in scal.get_events(e.dt_start, e.dt_end):
        assert ev.uid != e.uid


def test_handle_event():
    """Test handling (addition and removal) of events."""
    fname = 'test/data/lara-edwards-sundays.ics'
    body = open(fname).read()
    e = SEvent(body, '2021-07-07 12:00:00+02:00')

    cfname = 'test/data/lara-edwards-sundays-cancel.ics'
    cbody = open(cfname).read()
    ce = SEvent(cbody, '2021-07-07 12:00:00+02:00')

    assert e.uid == ce.uid

    scal = get_default_scal('cal-test-dont-delete')

    # faulty calendar operations
    # for ev in scal.get_events():
    #     assert ev.uid != e.uid

    scal.handle_event(body, '2021-06-06 12:00:00-02:00')

    was_found = False
    for ev in scal.get_events(e.dt_start, e.dt_end):
        if ev.uid == e.uid:
            was_found = True
    assert was_found

    scal.handle_event(cbody, '2021-06-08 12:00:00-02:00')

    for ev in scal.get_events(e.dt_start, e.dt_end):
        assert ev.uid != e.uid
