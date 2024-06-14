 """
REST endpoint.

TODO: make is_authorized and exception handling decorators.
"""

import functools
from flask import Flask, request
from werkzeug.exceptions import HTTPException
from cachetools import TTLCache
import json
import uuid

from common_utils import CONFIG, START_TIME, END_TIME, get_trace, DATES, get_logger
from course import CourseFactory
from teacher import get_teacher_factory, Teacher
from tc_schedule import SchedulerFactory, SUMMARY, DESCRIPTION

LOGGER = get_logger('webapp')
WEB_REQ = 'web_request'
WEB_RESP = 'web_response'
WEB_ID = 'web_ID'
WEB_NAME = 'web_name'

WEB_PFIX = CONFIG['WEB_ROOT']
WEB_PORT = CONFIG['WEB_PORT']

TEACHER_IDS = 'teacherIds'
TEACHER_ID = 'teacherId'
AVAILABLE = 'available'
HAS_CALENDAR = 'hasCalendar'
SCHEDULES = 'schedules'
INVITES = 'invites'
N_SCHEDULES = 'nSchedules'

SUCCESS = 'success'
MESSAGE = 'Message'
RESULT = 'Result'
DETAILS = 'Details'

API_KEY = 'api-key'

ENDPOINT_UP = {
    SUCCESS: True,
    MESSAGE: 'The endpoint is up',
}

UNAUTHORIZED = {
    SUCCESS: False,
    MESSAGE: 'Unauthorized',
}

BAD_REQUEST = {
    SUCCESS: False,
    MESSAGE: 'Bad Request',
}

UNKNOWN_ERROR = {
    SUCCESS: False,
    MESSAGE: 'Unknown Error',
    DETAILS: {},
}

TEACHER_CALENDAR = {
    SUCCESS: True,
    MESSAGE: 'Teacher Availability Calendar',
    RESULT: [],
}

TEACHER_AVAIL = {
    SUCCESS: False,
    MESSAGE: 'No available teachers found',
    RESULT: [],
}

TEACHER_SCHEDULE = {
    SUCCESS: False,
    MESSAGE: 'No teachers found for the given schedule',
    RESULT: [],
}

PING_SFIX = 'ping'
URL_PING = f'{WEB_PFIX}/{PING_SFIX}'

CAL_SFIX = 'calendar'
URL_TEACHER_CALENDAR = f'{WEB_PFIX}/{CAL_SFIX}'
OUT_DATES = 'dates'

SCHEDULE_SFIX = 'schedule'
URL_TEACHER_SCHEDULE = f'{WEB_PFIX}/{SCHEDULE_SFIX}'


app = Flask(__name__)


# TODO: This needs to be moved somewhere else, such as teacher factory.
teachers_cache = TTLCache(maxsize=1000, ttl=5)


def get_teacher_by_id(tid: int) -> Teacher:
    """Return a cached version of the teacher object."""
    try:
        teacher = teachers_cache[tid]
    except KeyError:
        tfact = get_teacher_factory()
        teacher = tfact.from_id(tid)
        teachers_cache[tid] = teacher
    return teacher


def is_authorized() -> bool:
    """Returns True if the request is authorized."""
    req_api_key = request.headers.get(API_KEY)
    api_key = CONFIG.get('REST_API_KEY')
    if not api_key:
        return True
    return api_key == req_api_key


def logged(func: callable):
    """Assumes the function is an entry point for requests. Logs inputs/outputs."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        dargs = request.get_json()
        rr_uuid = str(uuid.uuid4())
        LOGGER.info(json.dumps({WEB_ID: rr_uuid, WEB_NAME: func.__name__, WEB_REQ: dargs}))
        result = func(*args, **kwargs)
        LOGGER.info(json.dumps({WEB_ID: rr_uuid, WEB_NAME: func.__name__, WEB_RESP: result[0]}))
        return result
    return wrapper


@app.route(URL_PING, methods=['POST'])
@logged
def ping_handler():
    if not is_authorized():
        return UNAUTHORIZED, 200
    return ENDPOINT_UP, 200


@app.route(URL_TEACHER_CALENDAR, methods=['POST'])
@logged
def teacher_calendar_handler():
    """Handles requests for teacher calendar."""
    if not is_authorized():
        return UNAUTHORIZED, 200

    try:
        args = request.get_json()
        assert isinstance(args, dict)

        tids = args.get(TEACHER_IDS)
        assert isinstance(tids, list)

        start = args.get(START_TIME)
        end = args.get(END_TIME)

        out = TEACHER_CALENDAR.copy()
        out[RESULT] = []

        for tid in tids:
            to_add = {TEACHER_ID: tid, AVAILABLE: {}}
            teacher = get_teacher_by_id(int(tid))
            if teacher:
                to_add[AVAILABLE][OUT_DATES] = [ti.to_dict for ti in teacher.get_avail(start, end).dts()]
                to_add[AVAILABLE][INVITES] = teacher.get_invites(start, end)
            out[RESULT].append(to_add)
        return out, 200
    except AssertionError:
        return BAD_REQUEST, 200


@app.route('/dev/api/v1/schedule', methods=['POST'])
@logged
def schedule_handler_dev():
    """Dev-specific handler; uses special logic."""
    template = json.load(open('test/data/dev-schedule.json'))

    args = request.get_json()
    tids = args[TEACHER_IDS]
    n = args.get(N_SCHEDULES, 3)
    out = TEACHER_SCHEDULE.copy()
    out[RESULT] = []

    for tid in tids:
        to_add = {
            TEACHER_ID: tid,
            SCHEDULES: [],
            HAS_CALENDAR: True,
            AVAILABLE: True,
        }
        for i in range(n):
            to_add[SCHEDULES].append(template)
        out[RESULT].append(to_add)

    if n > 0:
        out[SUCCESS] = True
        out[MESSAGE] = 'Schedule is found'

    return out, 200


@app.route(URL_TEACHER_SCHEDULE, methods=['POST'])
@logged
def schedule_handler():
    """Figure out schedules for the class."""
    try:
        args = request.get_json()
        assert isinstance(args, dict)
        tids = args[TEACHER_IDS]
        assert isinstance(tids, list)

        n = args.get(N_SCHEDULES, 3)

        course = CourseFactory.from_req_dict(args)

        out = TEACHER_SCHEDULE.copy()
        out[RESULT] = []

        for tid in tids:
            teacher = get_teacher_by_id(int(tid))
            if not teacher:
                continue

            sch = SchedulerFactory.get(course, teacher)
            to_add = {
                TEACHER_ID: tid,
                SCHEDULES: [],
                HAS_CALENDAR: teacher.is_active,
                AVAILABLE: sch is not None,
            }

            if sch:
                avails = sch.schedules(n=n)
                for avail in avails:
                    to_add[SCHEDULES].append({
                        OUT_DATES: avail.to_dict[DATES],
                        # The params are not necessary; here in case we want to change them.
                        INVITES: avail.get_invites(**{
                            SUMMARY: course.name,
                            DESCRIPTION: course.name,
                        })
                    })

            out[RESULT].append(to_add)

        for rd in out[RESULT]:
            if rd.get(SCHEDULES):
                out[SUCCESS] = True
                out[MESSAGE] = 'Schedule is found'
        return out, 200
    except AssertionError:
        return BAD_REQUEST, 200


@app.errorhandler(Exception)
@logged
def exception_handler(ex):
    # pass through HTTP errors
    if isinstance(ex, HTTPException):
        return ex

    details = {
        'type': type(ex).__name__,
        'message': str(ex),
        'trace': get_trace(ex),
    }
    out = UNKNOWN_ERROR.copy()
    out[DETAILS] = details

    return out, 200


if __name__ == '__main__':
    app.run(debug=False, port=WEB_PORT)
