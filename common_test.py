"""
Pieces common to testing...
"""

from tc_event import SEventTentativeFactory, SEventCancelFactory, SEventAcceptFactory, \
    ORGANIZER, SUMMARY, TENTATIVE, CANCELLED, ACCEPTED, DT_START, DT_END, DT_STAMP, PARTICIPANTS
from client_email import EmailClient
from common_utils import CONFIG, DEFAULT_TZN, to_tz_dt
from datetime import datetime


invite_types = {
    ACCEPTED: SEventAcceptFactory(),
    TENTATIVE: SEventTentativeFactory(),
    CANCELLED: SEventCancelFactory(),
}


def send_avail_invite_test(
        uid: int, start: str, end: str,
        itype=TENTATIVE, target=CONFIG['EMAIL_USER'], tz_name=DEFAULT_TZN):
    """Send the avail invite from a fake user (TEST_USER 1/2/3)."""
    # TODO: better date start, date end, summary
    user = CONFIG[f'TEST_USER{uid}']
    host = CONFIG[f'TEST_HOST{uid}']
    pwd = CONFIG[f'TEST_PWD{uid}']
    assert itype in invite_types

    args = {
        ORGANIZER: user,
        SUMMARY: f'{user} available',
        DT_STAMP: to_tz_dt(tz_name, datetime.now()),
        DT_START: to_tz_dt(tz_name, start),
        DT_END: to_tz_dt(tz_name, end),
        PARTICIPANTS: [target],
    }

    invite = invite_types[itype].get_invite_str(**args)
    client = EmailClient(host=host, user=user, pwd=pwd)
    client.email_test_invite(user, target, invite)
