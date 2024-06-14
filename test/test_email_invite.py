"""
Testing email extraction functionality.

# TODO: real tests; the one below only spam.
"""

from time import sleep
from datetime import datetime, timedelta
from glob import glob

from client_email import EmailClient
from common_utils import config
from common_test import send_avail_invite_test
from teacher import TeacherFactoryAvail
from tc_event import TENTATIVE, CANCELLED, ACCEPTED


DATE_START = 'start'
DATE_END = 'end'


def test_invites():
    """Testing fetching invites only."""
    dates = {
        DATE_START: '2021-06-28 14:00:00',
        DATE_END: '2021-06-28 19:00:00'
    }
    send_avail_invite_test(1, **dates)

    dates = {
        DATE_START: '2021-06-26 10:00:00',
        DATE_END: '2021-06-26 16:00:00',
    }
    send_avail_invite_test(2, **dates)

    dates = {
        DATE_START: '2021-06-28 10:00:00',
        DATE_END: '2021-06-28 16:00:00',
    }
    send_avail_invite_test(2, **dates)

    sleep(5)

    client = EmailClient()
    invites = client.fresh_invites()
    senders = [invite.sender for invite in invites]

    assert 'dmarc@alvizion.com' in senders
    assert 'yakovk@alvizion.com' in senders
    for subject in [invite.subject for invite in invites]:
        assert 'avail' in subject


def test_send_confirmed():
    tfa = TeacherFactoryAvail(glob('test/data/test_schedule/teacher_*'))
    target = config()['TEST_USER1']
    email = EmailClient()
    teacher = tfa.from_email(target)
    # teacher.email = 'khurram.jhumra@gmail.com'
    email.send_confirmed(teacher)


def test_send_not_found():
    target = config()['TEST_USER1']
    # target = 'khurram.jhumra@gmail.com'
    email = EmailClient()
    email.send_not_found(target)


def test_one_off():
    """Check that the invite looks fine."""

    start = (datetime.now() + timedelta(days=2)).replace(microsecond=0).replace(second=0)
    end = start + timedelta(minutes=60)
    target = 'yakov.keselman@gmail.com'
    # target = 'yk@helvetiaeducation.ch'

    dates = {
        DATE_START: start,
        DATE_END: end,
    }
    if target:
        send_avail_invite_test(1, **dates, itype=ACCEPTED, target=target, tz_name='America/Chicago')
    else:
        send_avail_invite_test(1, **dates, itype=TENTATIVE, target=target, tz_name='America/Chicago')

    sleep(40)

    # send_avail_invite_test(1, **dates, itype=CANCELLED, target=target, tz_name='America/Chicago')
    send_avail_invite_test(1, **dates, itype=CANCELLED, target=target)
