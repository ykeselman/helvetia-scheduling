"""
Implements functionality of server-side calendar.

TODO: testing, more testing.
"""

from abc import ABC, abstractmethod
from typing import List, Union
from datetime import datetime
# from functools import lru_cache

import vobject
import caldav

from common_utils import CONFIG, Logged, TIFactory, DEFAULT_TZN, get_trace_str
from tc_event import SEvent


class DavClient(ABC):
    """Connection to a Cal Dav server."""

    def __init__(self, host='', user='', pwd=''):
        host = host or CONFIG['SCH_HOST']
        user = user or CONFIG['SCH_USER']
        pwd = pwd or CONFIG['SCH_PWD']
        caldav_url = self._url(host, user)
        self._client = caldav.DAVClient(url=caldav_url, username=user, password=pwd)

    @staticmethod
    @abstractmethod
    def _url(host: str, user: str):
        return ''

    @property
    def client(self) -> caldav.DAVClient:
        return self._client


class SogoDavClient(DavClient):
    """Connection to a SoGo server."""

    @staticmethod
    def _url(host: str, user: str):
        return f'https://{host}/SOGo/dav/{user}/Calendar/personal/'


# @lru_cache(maxsize=20)
def get_sogo_dav_client():
    return SogoDavClient()


class InfomDavClient(DavClient):
    """Connection to the InfoManiak server."""

    @staticmethod
    def _url(host: str, user: str):
        return f'https://{host}'


class SCalendar(Logged):
    """Server-side calendar."""

    @staticmethod
    def exists(dav: DavClient, name: str) -> caldav.Principal:
        """Returns calendar if found; if not, returns nothing."""
        client = dav.client
        principal = client.principal()
        try:
            return principal.calendar(name=name.lower())
        except caldav.error.NotFoundError:
            pass

    def __init__(self, dav: DavClient, name: str):
        client = dav.client
        principal = client.principal()
        # lower-case name to avoid mutiple entries...
        self.name = name.lower()

        try:
            self._cal = principal.calendar(name=self.name)
            self.is_new = False
            self.info("FOUND CALENDAR")
        except caldav.error.NotFoundError:
            self.info("DID NOT FIND CALENDAR")
            self._cal = principal.make_calendar(name=self.name)
            self.is_new = True
            self.info("CREATED CALENDAR")

    @property
    def log_name(self) -> str:
        return self.name

    @property
    def cal(self) -> caldav.Calendar:
        return self._cal

    def get_events(self, start: Union[datetime, str], end: Union[datetime, str]) -> List[SEvent]:
        """Returns a list of events."""
        tif = TIFactory(DEFAULT_TZN)
        ti = tif.from_se(start, end, '', '')
        events = self.cal.date_search(start=ti.start, end=ti.end, expand=True)
        return [SEvent(event, '') for event in events]

    def handle_event(self, event: str, dt: str) -> SEvent:
        """Handle the event. Returns the added or removed event."""
        e = SEvent(event, dt)
        if e.is_active:
            return self.add_event(event, dt)
        return self.delete_event(e.uid, e.dt_start, e.dt_end)

    def add_event(self, event: str, dt: str) -> SEvent:
        """Add event -- very basic. Returns the added event."""
        try:
            e = SEvent(self.cal.save_event(event), dt)
            self.info("ADDED NEW EVENT TO CALENDAR")
            return e
        except caldav.error.PutError:
            # TODO: handle certain exceptions, such as repeat fields
            self.info("PUT ERROR ADDING NEW EVENT TO CALENDAR")
        except vobject.base.ValidateError:
            # TODO: handle certain exceptions, such as repeat fields
            self.info("VALIDATION ERROR ADDING NEW EVENT TO CALENDAR")
        except Exception as ex:
            self.info(get_trace_str(ex))

    def delete_event(self, uid: str, start=None, end=None) -> SEvent:
        """Delete the event from the calendar, if exists."""
        tif = TIFactory(DEFAULT_TZN)
        ti = tif.from_se(start, end, '', '')
        events = self.cal.date_search(start=ti.start, end=ti.end, expand=True)
        deleted = None
        for event in events:
            e = SEvent(event, ti.start)
            if e.uid == uid:
                event_title = event.vobject_instance.vevent.summary.value
                event.delete()
                self.info(f"DELETED EVENT WITH TITLE {event_title}")
                return e
        if not deleted:
            self.info(f"COULD NOT FIND EVENT WITH UID {uid}")

    def remove(self):
        """Remove named calendar."""
        try:
            self.cal.delete()
            self.info("REMOVED CALEDAR")
        except caldav.error.NotFoundError:
            self.info("DID NOT FIND CALENDAR FOR REMOVAL")


# @lru_cache(maxsize=20)
def get_scalendar(dav: DavClient, name: str) -> SCalendar:
    return SCalendar(dav, name)


# @lru_cache(maxsize=20)
def get_default_scal(name: str) -> SCalendar:
    dav = get_sogo_dav_client()
    return SCalendar(dav, name)
