"""
The jobs that will be executed on a schedule.
"""

import schedule
import argparse
import time

from common_utils import CONFIG
from client_email import EmailClient
from teacher import get_teacher_factory


TF = get_teacher_factory()


def job_confirm_email(test_user=''):
    """
    Check the invite, respond with a confirm message if needed or disconfirm always.
    A calendar is only set up for existing teachers.
    """

    email = EmailClient()
    invites = email.fresh_invites()

    for invite in invites:
        sender = invite.sender
        if test_user and test_user != sender:
            continue
        teacher = TF.from_email(sender)
        if teacher:
            if not teacher.is_calendar_setup:
                email.send_confirmed(teacher)
        else:
            email.send_not_found(sender)


def get_add_event_func(invite_func: callable) -> callable:
    """Returns a fuction that executes one of the two invite types."""

    def job_add_event_proto(test_user=''):
        """
        Look in the appropriate invites folder.
        If the sender is in DB, create/update the calendar.
        Potentially, move the invite to a different folder.
        """

        email = EmailClient()
        invites = invite_func(email)

        for invite in invites:
            sender = invite.sender
            if test_user and test_user != sender:
                continue

            teacher = TF.from_email(sender)
            if not teacher:
                continue

            body = invite.cal_accepted
            if body:
                teacher.handle_event(body, invite.datetime)

    return job_add_event_proto


job_add_accepted_event = get_add_event_func(EmailClient.accepted_invites)
job_add_processed_event = get_add_event_func(EmailClient.processed_invites)
job_add_stored_event = get_add_event_func(EmailClient.stored_invites)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--forever', action='store_true', help='Keep doing it')
    args, unknown = parser.parse_known_args()

    if args.forever:
        email_mins = int(CONFIG['CONFIRM_EMAIL_MINUTES'])
        accept_mins = int(CONFIG['ACCEPTED_EVENT_MINUTES'])
        processed_mins = int(CONFIG['PROCESSED_EVENT_MINUTES'])
        stored_hours = int(CONFIG['STORED_EVENT_HOURS'])
        schedule.every(email_mins).minutes.do(job_confirm_email)
        schedule.every(accept_mins).minutes.do(job_add_accepted_event)
        schedule.every(processed_mins).minutes.do(job_add_processed_event)
        schedule.every(stored_hours).hours.do(job_add_stored_event)

        while True:
            schedule.run_pending()
            time.sleep(10)
    else:
        job_confirm_email()
        time.sleep(5)
        job_add_accepted_event()


# Schedule examples
# schedule.every(1).minutes.do(job)
# schedule.every().hour.do(job)
# schedule.every().day.at("10:30").do(job)
# schedule.every().monday.do(job)
# schedule.every().wednesday.at("13:15").do(job)
