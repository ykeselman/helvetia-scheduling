"""
Send and receive email, create calendar entries.
"""

import imaplib
import email
from email.header import decode_header
from typing import List, Tuple

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from common_utils import email_part, CONFIG, tagged, Logged, get_trace_str, formatted_template
from response_messages import NOT_FOUND, CONFIRMED, SUBJECT, MESSAGE, MESSAGES,\
    TEST_INVITE
from teacher import Teacher, EMAIL


TPLAIN = 'text/plain'
TCAL = 'text/calendar'


class EmailMessage(Logged):
    # class EmailMessage:

    """Message decomposed into parts."""

    @staticmethod
    def decoded(unk, encoding):
        if isinstance(unk, bytes):
            if encoding:
                return unk.decode(encoding)
            return unk.decode()
        return unk

    def __init__(self, msg):
        self._msg = msg
        self._body = ''
        self._from = 'nobody@nobody.nobody'
        self._subject = 'NO SUBJECT'
        self._cal = ''
        self._dt = ''

        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])

            self._dt = self.get_fval(msg, 'Date')
            self._subject = self.get_fval(msg, 'Subject')
            # Sometimes reply-to and from are different
            # Todo: figure out better approaches.
            sender = self.get_fval(msg, "From")
            reply_to = self.get_fval(msg, "Reply-To")

            if reply_to and reply_to != sender:
                sender = reply_to
            self._from = sender

            parts = [msg]
            if msg.is_multipart():
                parts = list(msg.walk())
                # TODO: figure out if there are multiple events per email; treat them separately.
            for part in parts:
                content_type = part.get_content_type()
                try:
                    if content_type == TPLAIN:
                        self._body = part.get_payload(decode=True).decode()
                    if content_type == TCAL:
                        self._cal = part.get_payload(decode=True).decode()
                except Exception as ex:
                    self.warning(get_trace_str(ex))
                    pass

    @property
    def log_name(self) -> str:
        return self.sender + ':' + self.subject

    def get_fval(self, msg, field: str) -> str:
        """Return field value as string."""
        fval = msg.get(field)
        if not fval:
            return ''
        val, encoding = decode_header(fval)[0]
        return self.decoded(val, encoding)

    @property
    def datetime(self) -> str:
        return self._dt

    @property
    def sender(self) -> str:
        return email_part(self._from)

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def body(self) -> str:
        return self._body

    @property
    def cal(self) -> str:
        return self._cal

    @property
    def cal_accepted(self) -> str:
        # TODO: make sure always works
        return self.cal.replace('NEEDS-ACTION', 'ACCEPTED')

    @property
    def is_invite(self):
        return len(self.cal) > 0


class EmailClient(Logged):
    """Connection to an IMAP email server for reading/sending emails."""

    INBOX = 'INBOX'
    ACCEPTED = 'accepted'
    PROCESSED = 'processed'
    STORAGE = 'storage'
    OTHER = 'other'
    OUT_PORT = 587

    def __init__(self, host='', user='', pwd='', user_name=''):
        self.host = host or CONFIG['EMAIL_HOST']
        self.user = user or CONFIG['EMAIL_USER']
        self.user_name = user_name or CONFIG['EMAIL_USER_NAME']
        self.pwd = pwd or CONFIG['EMAIL_PWD']

    @property
    def log_name(self) -> str:
        return self.user

    def inbox_message_cnt(self) -> int:
        """Returns the number of messages in INBOX to track received messages."""
        with imaplib.IMAP4_SSL(self.host) as server:
            server.login(self.user, self.pwd)
            status, messages = server.select('INBOX')
            return int(messages[0])

    def fresh_invites(self) -> List[EmailMessage]:
        """Move fresh invites from inbox to invites."""
        return self._invites(read_from=self.INBOX, move_to=self.ACCEPTED)

    def accepted_invites(self) -> List[EmailMessage]:
        """Move invites to the archive."""
        return self._invites(read_from=self.ACCEPTED, move_to=self.PROCESSED)

    def processed_invites(self) -> List[EmailMessage]:
        """Store them here to make sure none are missing..."""
        return self._invites(read_from=self.PROCESSED, move_to=self.STORAGE)

    def stored_invites(self) -> List[EmailMessage]:
        """Store them here to make sure none are missing..."""
        return self._invites(read_from=self.STORAGE, move_to=self.STORAGE)

    def _invites(self, read_from: str, move_to: str) -> List[EmailMessage]:
        """
        Returns invites. Reads them from read_from and moves them to move_to.
        Emails that are not invites are moved to 'other'.
        TODO: separate into valid and invalid invites, potentially...
        TODO: depends on whether we get many invalid invites or not...
        """
        out = []
        with imaplib.IMAP4_SSL(self.host) as server:
            server.login(self.user, self.pwd)
            if read_from == move_to:
                self.info(f"GETTING MESSAGES FROM: {read_from}")
            else:
                self.info(f"MOVING MESSAGES FROM: {read_from} TO: {move_to}")
            status, messages = server.select(read_from)
            try:
                total = int(messages[0])
                for i in range(total):
                    idx = str(i+1)
                    res, msg = server.fetch(idx, "(RFC822)")
                    elt = EmailMessage(msg)
                    if elt.is_invite:
                        out.append(elt)
                        msg_move_to = move_to
                    else:
                        msg_move_to = self.OTHER
                    if read_from != msg_move_to:
                        server.create(msg_move_to)
                        server.copy(idx, msg_move_to)
                        server.store(idx, '+FLAGS', r"\Deleted")
                server.expunge()
            except Exception as e:
                self.warning(f"GOT EXCEPTION: {get_trace_str(e)}")
            return out

    def _send_email(self, target: str, subject: str, message: str, invite: str = None):
        """Send email from the address. May include a string invite."""

        if invite:
            out = MIMEMultipart('mixed')
        else:
            out = MIMEMultipart("alternative")
        out["Subject"] = subject
        out["From"] = f"{self.user_name} <{self.user}>" if self.user_name else self.user
        out["To"] = target

        part1 = MIMEText(message)
        out.attach(part1)

        if invite:
            part_cal = MIMEText(invite, 'calendar;method=REQUEST')
            msg_alt = MIMEMultipart('alternative')
            msg_alt.attach(part_cal)
            out.attach(msg_alt)

        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.OUT_PORT) as server:
            try:
                server.starttls(context=context)
                server.login(self.user, self.pwd)
                server.sendmail(self.user, target, out.as_string())
                self.info(f'Sent email to: {target} with subject: {subject}')
            except smtplib.SMTPDataError as ex:
                self.warning(get_trace_str(ex))

    def send_confirmed(self, teacher: Teacher):
        """Send out confirmation email."""
        subject, body = self.get_subject_body(CONFIRMED, teacher.to_dict)
        self._send_email(teacher.email, subject, body)

    def send_not_found(self, target: str):
        """Send out disconfirmation email."""
        subject, body = self.get_subject_body(NOT_FOUND, {EMAIL: target})
        self._send_email(target, subject, body)

    def email_test_invite(self, source: str, target: str, invite: str):
        """Send out test invite email. Needs to be as string already."""
        subject, body = self.get_subject_body(TEST_INVITE, {EMAIL: source})
        self._send_email(target, subject, body, invite)

    @staticmethod
    def get_subject_body(mail_type: str, vals: dict) -> Tuple[str, str]:
        """Returns subject and body for the given email type."""
        nf = tagged(MESSAGES, mail_type)
        return formatted_template(nf[SUBJECT], vals), formatted_template(nf[MESSAGE], vals)
