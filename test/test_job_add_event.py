"""
Testing of the add event functionality.
See that invites get added to the right calendar...
"""

from client_calendar import SCalendar, get_scalendar, get_sogo_dav_client
from common_utils import config
from crontab_jobs import job_add_accepted_event, job_confirm_email, job_add_processed_event, job_add_stored_event
from common_test import send_avail_invite_test


def loop_test_cal(uid: int, teacher: bool):
    """
    Send new events.
    Make sure they are added.
    Make sure acknowledgements are received.
    """

    conf = config()
    user = conf[f'TEST_USER{uid}']

    # TODO: need the email confirmation for add event to work...
    # TODO: think about it -- separate func or OK???
    job_confirm_email(user)
    job_add_accepted_event(user)
    job_add_processed_event(user)
    job_add_stored_event(user)

    dav = get_sogo_dav_client()
    cdav = SCalendar.exists(dav, user)
    if teacher:
        assert cdav
        scal = get_scalendar(dav, user)
        events = scal.get_events('2021-12-28', '2021-12-29')
        assert len(events) > 0
    else:
        assert not cdav


def test1():
    send_avail_invite_test(1, '2021-12-28 14:00:00', '2021-12-28 19:00:00')
    loop_test_cal(1, teacher=True)


def test2():
    send_avail_invite_test(2, '2021-12-28 10:00:00', '2021-12-28 16:00:00')
    loop_test_cal(2, teacher=True)


def test3():
    send_avail_invite_test(3, '2021-12-27 10:00:00', '2021-12-27 16:00:00')
    loop_test_cal(3, teacher=False)
