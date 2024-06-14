"""
Testing of the email confirmation functionality.

- send invite from a fake user to the invite address.
- run the invite confirmation script.
- make sure that confirmations were sent.
- make sure for each bad invite a disconfirmation was sent.
"""
from time import sleep
from datetime import datetime, timedelta

from client_calendar import get_sogo_dav_client, get_scalendar, SCalendar
from client_email import EmailClient
from common_utils import config
from common_test import send_avail_invite_test
from crontab_jobs import job_confirm_email


def loop_test_invite(uid: int, teacher: bool, do_del: bool):
    """
    Remove calendar from cal server.
    Send new events.
    Make sure they are added.
    Make sure acknowledgements are received.
    """

    conf = config()
    user = conf[f'TEST_USER{uid}']
    dav = get_sogo_dav_client()

    # remove the user's calendar
    if do_del:
        if SCalendar.exists(dav, user):
            cal = get_scalendar(dav, user)
            cal.remove()

    uemail = EmailClient(
        host=conf[f'TEST_HOST{uid}'],
        user=user,
        pwd=conf[f'TEST_PWD{uid}'],
    )

    msg_cnt = uemail.inbox_message_cnt()

    # move all prev invites
    email = EmailClient()
    _ = email.fresh_invites()

    start = (datetime.now() + timedelta(days=2)).replace(
        microsecond=0).replace(second=0).replace(minute=0)
    end = start + timedelta(minutes=60)
    invites = [(str(start + timedelta(days=i+1)), str(end + timedelta(days=i+1))) for i in range(5)]

    if do_del:
        invites = invites[:2]
    else:
        invites = invites[2:]

    for invite in invites:
        send_avail_invite_test(uid, invite[0], invite[1])
        sleep(3)

    job_confirm_email(user)

    sleep(3)
    new_msg_cnt = uemail.inbox_message_cnt()

    # TODO: make sure different emails were sent: confirmed or not found
    if teacher:
        # only a single confirmation email should have been sent
        assert new_msg_cnt - msg_cnt == int(do_del)
    else:
        # for each faulty invite, send a message.
        assert new_msg_cnt - msg_cnt == len(invites)


def test1():
    loop_test_invite(1, teacher=True, do_del=True)
    loop_test_invite(1, teacher=True, do_del=False)


def test2():
    loop_test_invite(2, teacher=True, do_del=True)
    loop_test_invite(2, teacher=True, do_del=False)


def test3():
    loop_test_invite(3, teacher=False, do_del=True)
    loop_test_invite(3, teacher=False, do_del=False)
