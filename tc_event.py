"""
Various event-related functionality...
Mostly uses already provided methods from CalDav etc. An adapter, essentially.

Functionality having to do with generating (maybe parsing) of calendar invites.

TODO: testing

"""

from typing import List, Union
from abc import ABC  # , abstractmethod

import pandas as pd
import recurring_ical_events
import caldav
import icalendar as ical
from icalendar import vCalAddress, vText, vRecur, vDDDTypes
from datetime import datetime

from common_utils import TimeInterval, CONFIG, Logged, to_tz_dt, TIFactory
from cal_time_zones import get_tz_name, get_cal_tz

STATUS = 'status'
ACCEPTED = 'accepted'
TENTATIVE = 'tentative'
CANCELLED = 'cancelled'

SFIX_ACCEPTED = f' **{ACCEPTED}**'
SFIX_CANCELLED = f' **{CANCELLED}**'
SFIX_TENTATIVE = f' **{TENTATIVE}**'
MAKE_BUSY = 'make_busy'

# Some important event fields
SUMMARY = 'SUMMARY'
DT_START = 'DTSTART'
DT_END = 'DTEND'
UID = 'UID'
CANCEL = 'CANCEL'
REQUEST = 'REQUEST'
ADD = 'ADD'
LAST_MODIFIED = 'LAST-MODIFIED'

# Organizer is a bit tricky to extract???
# The below are mostly for putting together events, not extractig fields
ORGANIZER = 'ORGANIZER'
NAME = 'CN'
EMAIL = 'email'
ROLE = 'role'
ROLE_ORG = 'CHAIR'
ROLE_PART = 'REQ-PARTICIPANT'
RSVP = 'RSVP'
RSVP_TRUE = 'TRUE'
CUTYPE = 'cutype'
CUTYPE_IND = 'individual'
PART_STAT = 'partstat'

PART_STAT_ACC = 'ACCEPTED'
PART_STAT_NEED = 'NEEDS-ACTION'

TRANSP = 'TRANSP'
TRANSP_OPAQUE = 'OPAQUE'
TRANSP_TRANSP = 'TRANSPARENT'
SEQUENCE = 'SEQUENCE'
CREATED = 'CREATED'
PARTICIPANTS = 'PARTICIPANTS'
ATTENDEE = 'ATTENDEE'

PRODID = 'PRODID'
VERSION = 'VERSION'
METHOD = 'METHOD'
DT_STAMP = 'DTSTAMP'
RRULE = 'RRULE'
UNTIL = 'UNTIL'

# Not always reliable
DESCRIPTION = 'DESCRIPTION'
LOCATION = 'LOCATION'
CALSCALE = 'CALSCALE'

TIMEZONE = 'timezone'


class SEvent(Logged):
    """Server-side event: read from a calendar server, use for availability."""

    def __init__(self, cal_event: object, last_modified: object):
        """Populate from the event, which can be ical.Event, caldav.Event or body."""
        self._ical = None
        self._body = 'NO BODY'
        self._fields = {}
        self._last_modified = None

        if isinstance(cal_event, ical.Calendar):
            self._ical = cal_event
            self._body = '\n'.join([line for line in cal_event.content_lines() if line])
        elif isinstance(cal_event, caldav.Event):
            cal_event = cal_event.icalendar_instance
            self._body = cal_event.to_ical().decode()
        elif isinstance(cal_event, str):
            self._body = cal_event
        else:
            raise Exception("INVALID CALENDAR/EVENT TYPE")

        if not self._ical:
            self._ical = ical.Calendar.from_ical(self._body)
        for event in self._ical.subcomponents:
            self._fields.update(event)

        if isinstance(last_modified, datetime):
            self._last_modified = last_modified

        # TODO: re-work this.
        if not self._last_modified:
            try:
                self._last_modified = to_tz_dt(self.tz_name, last_modified)
            except Exception:
                pass

        if not self._last_modified:
            try:
                self._last_modified = self._fields.get(LAST_MODIFIED, '').dt
            except AttributeError:
                pass

        if not self._last_modified:
            self._last_modified = to_tz_dt(self.tz_name, datetime.now())

    @property
    def dt_start(self) -> datetime:
        return self._fields.get(DT_START).dt

    @property
    def dt_end(self) -> datetime:
        return self._fields.get(DT_END).dt

    @property
    def tz_name(self) -> str:
        """Returns one of standard time zone names."""
        return get_tz_name(self._ical)

    @property
    def log_name(self) -> str:
        return self.summary

    @property
    def summary(self) -> str:
        return self._fields.get(SUMMARY, '')

    @property
    def body(self) -> str:
        return self._body

    @property
    def last_modified(self) -> datetime:
        return self._last_modified

    @property
    def _action(self) -> str:
        """Returns add or cancel."""

        status = self._fields.get(STATUS, '')
        if status:
            if CANCEL in status:
                return CANCEL

        if "METHOD:CANCEL" in self.body:
            return CANCEL

        if "STATUS:CANCEL" in self.body:
            return CANCEL

        return ADD

    @property
    def is_active(self) -> bool:
        return self._action not in [CANCEL]

    @property
    def is_busy(self) -> bool:
        """Returns True if it's a busy/confirmation rather than availability."""
        # TODO: a better job.
        return len(self.summary.split('*')) >= 5

    def dts(self, start=None, end=None) -> List[TimeInterval]:
        """Returns the list of days and times the event is active."""
        if not start:
            start = '2010-10-10'
        if not end:
            end = '3003-03-03'
        tif = TIFactory(self.tz_name)
        ti = tif.from_se(start, end)
        events = recurring_ical_events.of(self._ical).between(ti.start, ti.end)
        return [tif.from_se(
            event[DT_START].dt, event[DT_END].dt, 'name', self.summary) for event in events]

    @property
    def uid(self) -> str:
        return self._fields.get('UID')

    def __str__(self) -> str:
        # TODO: better output if it's useful...
        return '\n'.join([
            '-' * 80,
            f'UID: {self.uid}',
            # f'Organizer: {self.organizer}',
            f'Summary: {self.summary}',
            f'Last Modified: {self.last_modified}',
            f'Is Active: {self.is_active}',
            f'Start date: {self.dt_start}',
            f'End date:   {self.dt_end}',
            'Dates and times available:',
            str(pd.DataFrame([{'start': elt.start, 'end': elt.end} for elt in self.dts()])),
            # '-' * 20,
            # self.body,
            '-' * 80,
        ])


class SEventFactory(ABC):
    """Generates invite events -- something that will be sent out."""

    method = REQUEST
    sequence = 0
    status = ACCEPTED
    suffix = f' **{status}**'

    def get_sevent(self, **kwargs) -> SEvent:
        """Produce SEvent from ical."""
        # TODO: extract timestamp from kwargs.
        return SEvent(self.get_invite(**kwargs), '')

    def get_invite(self, **kwargs) -> ical.Calendar:
        """Generate an invite from arguments."""

        cal = ical.Calendar()
        cal[PRODID] = 'HEG Calendar//EN'
        cal[VERSION] = '2.0'
        cal[METHOD] = self.method
        cal[CALSCALE] = 'GREGORIAN'

        start = kwargs[DT_START]
        tz_name = str(start.tzinfo)
        cal.add_component(get_cal_tz(tz_name).get_ical_timezone(start))

        participants = kwargs.get(PARTICIPANTS, [CONFIG['SCH_USER']])
        assert len(participants) > 0
        kwargs[METHOD] = self.method
        kwargs[SEQUENCE] = self.sequence
        kwargs[STATUS] = self.status
        event = ical.Event()
        oemail = kwargs.get(ORGANIZER, CONFIG['EMAIL_USER'])

        event[DT_STAMP] = vDDDTypes(kwargs[DT_STAMP])
        event[DT_START] = vDDDTypes(kwargs[DT_START])
        event[DT_END] = vDDDTypes(kwargs[DT_END])
        date_start = event[DT_START].to_ical().decode()
        date_end = event[DT_END].to_ical().decode()

        oemail0 = oemail.split('@')[0]
        pemail0 = participants[0].split('@')[0]
        event[UID] = f'{date_start}:{date_end}:{oemail0}:{pemail0}'
        event[SUMMARY] = kwargs[SUMMARY]

        # TODO: where do we want to keep it?
        # TODO: maybe move to the body instead...
        if kwargs.get(MAKE_BUSY, True):
            event[SUMMARY] += self.suffix
            event[DESCRIPTION] = kwargs.get(DESCRIPTION, '')
            event[DESCRIPTION] += self.suffix

        event[TRANSP] = kwargs.get(TRANSP, TRANSP_OPAQUE)
        event[LOCATION] = kwargs.get(LOCATION, '')

        if RRULE in kwargs:
            event[RRULE] = vRecur(**kwargs[RRULE])

        event[SEQUENCE] = kwargs[SEQUENCE]

        org = vCalAddress(f'mailto:{oemail}')
        org.params[NAME] = vText(kwargs.get(NAME, CONFIG['EMAIL_USER_NAME']))
        org.params[EMAIL] = vText(oemail)
        org.params[ROLE] = vText(ROLE_ORG)
        org.params[PART_STAT] = vText(PART_STAT_ACC)
        event[ORGANIZER] = org

        for pemail in participants:
            # TODO: change to constants
            attendee = vCalAddress(f'mailto:{pemail}')
            attendee.params[NAME] = vText(pemail)
            attendee.params[ROLE] = vText(ROLE_PART)
            status = kwargs.get(STATUS, TENTATIVE)
            if status == ACCEPTED:
                attendee.params[PART_STAT] = vText(PART_STAT_ACC)
            else:
                attendee.params[PART_STAT] = vText(PART_STAT_NEED)
                attendee.params[RSVP] = vText(RSVP_TRUE)
            event.add(ATTENDEE, attendee, encode=0)

        cal.add_component(event)

        return cal

    def get_invite_str(self, **kwargs) -> str:
        """Return an invite as an embeddable string, with TZ included."""
        cal = self.get_invite(**kwargs)
        return cal.to_ical().decode().replace('\r\n', '\n').strip()


class SEventTentativeFactory(SEventFactory):
    """Tentative invite"""
    method = REQUEST
    sequence = 0
    status = TENTATIVE


class SEventCancelFactory(SEventFactory):
    """Cancelled invite"""
    method = CANCEL
    sequence = 1
    status = CANCELLED


class SEventAcceptFactory(SEventFactory):
    """Accepted invite"""
    method = REQUEST
    sequence = 0
    status = ACCEPTED
