"""
Details for teachers, including emails and ID's.
"""

from typing import List, Union
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import requests

from common_utils import CONFIG, ENV, START_TIME, END_TIME, JsonSer, Logged, MOCK, DEFAULT_TZN, TIFactory
from client_calendar import get_default_scal, SEvent
from available import Available, REQUEST, AvailableFactory
from course import TIMEZONE


ID = 'id'
EMAIL = 'email'
FNAME = 'first_name'
LNAME = 'last_name'

AFNAME = 'firstName'
ALNAME = 'lastName'
AID = 'Id'
AVAIL = 'availability'


class Teacher(JsonSer, Logged):
    """A single teacher instance: email, id, FN, LN, for now."""
    def __init__(self, email: str, tid: str, fn: str, ln: str):
        self.email = email
        self.id = tid
        self.fn = fn
        self.ln = ln
        self.avail: Available
        self.avail = None

    def __str__(self):
        return f'{self.fn} {self.ln}: {self.email}/{self.id}'

    @property
    def log_name(self) -> str:
        return self.email

    # can we cache it???
    # @cachedproperty
    @property
    def calendar(self):
        return get_default_scal(self.email)

    def handle_event(self, body: str, dt: str) -> SEvent:
        """Add/remove the event from the calendar."""
        return self.calendar.handle_event(body, dt)

    def get_events(self, start: Union[datetime, str], end: Union[datetime, str]) -> List[SEvent]:
        """The events in the range."""
        return self.calendar.get_events(start, end)

    def get_invites(self, start: Union[datetime, str], end: Union[datetime, str]) -> List[str]:
        events = self.get_events(start, end)
        if events:
            return [event.body for event in events]
        avail = self.get_avail(start, end)
        return [pair[REQUEST] for pair in avail.get_invites()]

    def get_avail(self, start: Union[datetime, str], end: Union[datetime, str]) -> Available:
        """The intervals in the range."""
        if not self.avail:
            events = self.calendar.get_events(start, end)
            self.avail = AvailableFactory.from_events(self.email, events, start, end)
        return self.avail

    @property
    def is_calendar_setup(self) -> bool:
        """Returns True if the calendar has already been set up."""
        # TODO: better way of doing it.
        return not self.calendar.is_new

    @property
    def is_active(self) -> bool:
        start = '2021-07-01'
        end = datetime.now() + timedelta(days=365)
        return (self.avail is not None) or (self.is_calendar_setup and len(self.get_events(start, end)) > 0)

    @property
    def to_dict(self) -> dict:
        return {
            EMAIL: self.email,
            ID: self.id,
            FNAME: self.fn,
            LNAME: self.ln,
            AVAIL: self.avail.dts() if self.avail else [],
        }

    def init_avail_from_avail(self, tz_name: str, dates: List[dict]):
        """Initializes availability from the availability info. Mainly, for testing."""
        self.avail = Available(self.email, tz_name)
        tif = TIFactory(tz_name)
        for date in dates:
            self.avail.add_interval(
                tif.from_se(date[START_TIME], date[END_TIME], 'email', self.email))


class TeacherFactory(ABC):
    """One of teacher factories."""

    @abstractmethod
    def from_email(self, email: str) -> Teacher:
        pass

    @abstractmethod
    def from_id(self, tid: int) -> Teacher:
        pass

    @staticmethod
    def from_dict(dd: dict) -> Teacher:
        if EMAIL in dd and ID in dd and FNAME in dd and LNAME in dd:
            return Teacher(dd[EMAIL], dd[ID], dd[FNAME], dd[LNAME])


class TeacherFactoryRest(TeacherFactory):
    """Find the teacher in the DB via REST."""

    def __init__(self):
        self.headers = {
            'Accept': 'application/json',
            'api-key': CONFIG['REST_API_KEY'],
        }
        self.url = CONFIG['REST_URL']

    def post_dict(self, dd: dict) -> Teacher:
        req = requests.post(self.url, headers=self.headers, json=dd)
        return self.from_dict(json.loads(req.text))

    def from_email(self, email: str) -> Teacher:
        """Look up the teacher in the DB."""
        return self.post_dict({EMAIL: email})

    def from_id(self, tid: int) -> Teacher:
        """Look up the teacher in the DB."""
        return self.post_dict({ID: tid})


class TeacherFactoryAvail(TeacherFactory):
    """From the mocked-up data."""

    def __init__(self, fnames: List[str]):
        """Create a teacher from availability info."""
        self.by_id = {}
        self.by_email = {}
        for fname in fnames:
            dd = json.load(open(fname))
            fname = dd[AFNAME]
            lname = dd[ALNAME]
            email = dd.get(EMAIL, f'{fname}.{lname}@some.com')
            teacher = Teacher(email, dd[AID], fname, lname)
            teacher.init_avail_from_avail(dd.get(TIMEZONE, DEFAULT_TZN), dd[AVAIL])
            self.by_id[dd[AID]] = teacher
            self.by_email[email] = teacher

    def from_email(self, email: str) -> Teacher:
        return self.by_email.get(email)

    def from_id(self, tid: int) -> Teacher:
        return self.by_id.get(tid)

    @property
    def ids(self) -> List[int]:
        return list(self.by_id.keys())


def sample_teachers_factory() -> TeacherFactory:
    """Returns a factory for sample teachers."""
    from glob import glob
    fnames = glob('test/data/test_schedule/teacher_*')
    return TeacherFactoryAvail(fnames)


def real_teachers_factory() -> TeacherFactory:
    """Returns a factory for real teachers."""
    return TeacherFactoryRest()


def get_teacher_factory() -> TeacherFactory:
    """Get one of the teacher factories."""
    if CONFIG[ENV] == MOCK:
        return sample_teachers_factory()
    return real_teachers_factory()
