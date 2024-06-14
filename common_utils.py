import os
import re
from dotenv import dotenv_values
from datetime import timedelta, datetime
import logging
from dateutil.parser import parse as date_parse
import pytz
from intervaltree import Interval

from abc import ABC, abstractmethod
from typing import List, Union

from threading import Thread
import functools


START_TIME = 'startTime'
END_TIME = 'endTime'
DATES = 'dates'
NAME = 'name'

ENV = 'ENV'
DEV = 'dev'
PROD = 'prod'
MOCK = 'mock'
STAGING = 'staging'

DEFAULT_TZN = 'Europe/Paris'


@functools.lru_cache(maxsize=1024)
def get_tz(tz_name: str):
    """Returns a time zone for annotating date times."""
    try:
        return pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        return pytz.timezone(DEFAULT_TZN)


def utc_normalize(dt: datetime) -> datetime:
    """Return UTC-normalized version of date time."""
    tz = get_tz(DEFAULT_TZN)
    try:
        dt = tz.localize(dt)
    except ValueError:
        pass
    return pytz.utc.normalize(dt)


def to_tz_dt(tz_name: str, obj: object, ignore_tz=False) -> datetime:
    """Convert to time-zoned datetime."""
    dt = None

    if isinstance(obj, datetime):
        dt = obj.replace(microsecond=0)
    elif isinstance(obj, str):
        dt = date_parse(obj)

    assert dt

    tz = get_tz(tz_name)
    try:
        return tz.localize(dt)
    except ValueError:
        locd = tz.localize(date_parse(str(dt)[:19]))
        if ignore_tz:
            return locd
        # convert to the specified TZ offset.
        return locd + (dt - locd)


def formatted_template(fmt: str, kv: dict) -> str:
    """A template formatted into plain text."""
    sep = '\n\n'
    parts = fmt.split(sep)
    out = [part.replace('\n', ' ').format(**kv) for part in parts]
    return sep.join(out).strip()


def config(my_env='') -> dict:
    """Returns the appropriate config file."""
    if not my_env:
        my_env = os.getenv(ENV, 'dev')
    return dotenv_values(f'settings/{my_env}/.env')


CONFIG = config()


def get_logger(app: str):
    """Default logger -- more configurable later..."""
    format_ = '[%(asctime)s] [%(levelname)s] %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S %z'
    my_env = CONFIG[ENV]
    filename = f'{app}-{my_env}.log'
    logger = logging.getLogger(f'{app}-{my_env}')
    logging.basicConfig(
        filename=filename,
        format=format_,
        datefmt=datefmt,
        level=logging.INFO
    )
    return logger


class Logged(ABC):
    """Logging functionality."""

    logger = get_logger('calendaring')

    @abstractmethod
    def log_name(self) -> str:
        pass

    def info(self, msg: str):
        """Logging functionality."""
        self.logger.info(f'[{self.log_name}]: {msg}')

    def warning(self, msg: str):
        """Logging functionality."""
        self.logger.warning(f'[{self.log_name}]: {msg}')


class JsonSer(ABC):
    """JSON Serializable object through as_dict."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Needs to return a JSON-serializable dict."""
        # TODO: potentially, go back to custom serializer; not clear why it did not work...
        pass


class TimeInterval(JsonSer, Interval):
    """Time interval: start/end and optional labe/value pair."""

    def __new__(cls, start: datetime, end: datetime, label='name', value='no-name'):
        """Instead of new; to be compatible with the superclass methods."""
        out = Interval.__new__(cls, start, start + (end - start), (label, value))
        out.label = label
        out.value = value
        return out

    @property
    def start(self):
        return self.begin

    @property
    def duration(self) -> int:
        """Returns the length in minutes."""
        return int((self.end - self.start).total_seconds()/60)

    def __str__(self) -> str:
        return f'{str(self.start)} --> {str(self.end)}'

    @property
    def to_dict(self) -> dict:
        return {
            self.label: self.value,
            'startTime': str(self.begin).replace(' ', 'T'),
            'endTime': str(self.end).replace(' ', 'T'),
        }


class TIFactory:
    """Produces Time Intervals from various things..."""

    def __init__(self, tz_name: str):
        self.tz_name = tz_name

    def from_interval(self, ti: TimeInterval) -> TimeInterval:
        return self.from_se(ti.start, ti.end, ti.label, ti.value)

    def from_se(
            self,
            start: Union[datetime, str], end: Union[datetime, str],
            label='name', value='none') -> TimeInterval:
        start = to_tz_dt(self.tz_name, start)
        end = to_tz_dt(self.tz_name, end)
        return TimeInterval(start, end, label, value)

    def from_tidd(self, d: dict, kw='') -> TimeInterval:
        """Parses entries encoded by date dicts."""
        start = to_tz_dt(self.tz_name, d[START_TIME])
        end = to_tz_dt(self.tz_name, d[END_TIME])
        return TimeInterval(start, end, kw, d.get(kw, ''))

    @staticmethod
    def merged_list(to_merge: List[TimeInterval]) -> List[TimeInterval]:
        """Returns a list of merged time intervals."""
        to_merge.sort()
        out = []
        if not to_merge:
            return []
        for ti in to_merge:
            if not out:
                out.append(ti)
                continue
            tii = out[-1]
            merged = TIFactory.union(tii, ti)
            if merged:
                out[-1] = merged
            else:
                out.append(ti)
        return out

    @staticmethod
    def intersect(t1: TimeInterval, t2: TimeInterval, label='', value='') -> Union[TimeInterval, None]:
        """Returns an interval that is the intersection of the two."""
        if not label:
            label = t1.label
        if not value:
            value = t1.value
        if t1.start > t2.start:
            return TIFactory.intersect(t2, t1, label, value)
        # assert t1.start <= t2.start
        if t1.end <= t2.start:
            return None
        if t1.end >= t2.end:
            return TimeInterval(t2.start, t2.end, label, value)
        # assert t2.start < t1.end < t2.end
        return TimeInterval(t2.start, t1.end, label, value)

    @staticmethod
    def reduced(ti: TimeInterval, duration: int, label='', value='') -> Union[TimeInterval, None]:
        """Reduces the original by the number of minutes."""
        if duration > ti.duration:
            return None
        start = ti.start + timedelta(minutes=duration)
        if not label:
            label = ti.label
        if not value:
            value = ti.value
        return TimeInterval(start, ti.end, label, value)

    @staticmethod
    def initial(ti: TimeInterval, duration: int, label='', value='') -> Union[TimeInterval, None]:
        """Initial part of the time interval."""
        if duration > ti.duration:
            return None
        end = ti.start + timedelta(minutes=duration)
        if not label:
            label = ti.label
        if not value:
            value = ti.value
        return TimeInterval(ti.start, end, label, value)

    @staticmethod
    def updated(ti: TimeInterval, tihm: TimeInterval) -> TimeInterval:
        """Set hours and minutes from tihm."""
        start = ti.start.replace(hour=tihm.start.hour, minute=tihm.start.minute)
        end = ti.end.replace(hour=tihm.end.hour, minute=tihm.end.minute)
        return TimeInterval(start, end)

    @staticmethod
    def union(ti1: TimeInterval, ti2: TimeInterval) -> Union[TimeInterval, None]:
        if ti1.end >= ti2.start > ti1.start:
            return TimeInterval(ti1.start, ti2.end, ti1.label, ti1.value)

    @staticmethod
    def overlaps(ti1: TimeInterval, ti2: TimeInterval) -> bool:
        """Returns true if the two overlap."""
        return TIFactory.intersect(ti1, ti2) is not None

    @staticmethod
    def diff(ti1: TimeInterval, ti2: TimeInterval) -> List[TimeInterval]:
        """Returns the difference between the two time intervals, 0 or 1 or 2 elements."""
        common = TIFactory.intersect(ti1, ti2)
        if not common:
            return [ti1]
        res = []
        if common.start > ti1.start:
            res.append(TimeInterval(ti1.start, common.start, ti1.label, ti1.value))
        if common.end < ti1.end:
            res.append(TimeInterval(common.end, ti1.end, ti1.label, ti1.value))
        return res


def email_part(s: str):
    """Extract email part of string."""
    # TODO: make sure it works...
    if ' ' in s or ':' in s:
        match = re.search(r'[\w.-]+@[\w.-]+', s)
        return match.group(0)
    return s


def tagged(entries: List[dict], tag: str) -> dict:
    """Return the entry with the tag."""
    for entry in entries:
        if 'tag' in entry and entry['tag'] == tag:
            return entry
    return {}


def timeout(seconds_before_timeout: int):
    """
    Produce a timer that throws an exception when the timeout is exceeded.
    https://stackoverflow.com/questions/21827874/timeout-a-function-windows
    """
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = [Exception('function [%s] timeout [%s seconds] exceeded!' % (
                func.__name__, seconds_before_timeout))]

            def new_func():
                try:
                    res[0] = func(*args, **kwargs)
                except Exception as ex:
                    res[0] = ex

            t = Thread(target=new_func)
            t.daemon = True
            try:
                t.start()
                t.join(seconds_before_timeout)
            except Exception as e:
                logging.warning('error starting thread')
                raise e
            ret = res[0]
            if isinstance(ret, BaseException):
                raise ret
            return ret

        return wrapper

    return deco


def get_trace(ex: Exception) -> List[str]:
    """Return trace as a list."""
    # https://stackoverflow.com/questions/1278705/when-i-catch-an-exception-how-do-i-get-the-type-file-and-line-number
    trace = []
    tb = ex.__traceback__
    while tb is not None:
        trace.append("{filename}:{lineno}:{name}".format(
            filename=os.path.split(tb.tb_frame.f_code.co_filename)[1],
            name=tb.tb_frame.f_code.co_name,
            lineno=tb.tb_lineno
        ))
        tb = tb.tb_next
    return trace


def get_trace_str(ex: Exception) -> str:
    """Single trace string."""
    return '\n'.join(get_trace(ex))
