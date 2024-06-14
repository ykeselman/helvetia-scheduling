"""
Test for the app.
"""

import json
from requests import post
from abc import ABC, abstractmethod
from typing import List
import pytest
from datetime import datetime, timedelta

from common_utils import config, PROD, DEV, MOCK, STAGING, START_TIME, END_TIME
from app import CAL_SFIX, PING_SFIX, SCHEDULE_SFIX, API_KEY, TEACHER_IDS, AVAILABLE, \
    SUCCESS, MESSAGE, RESULT, TEACHER_ID, OUT_DATES, SCHEDULES, INVITES, DETAILS, N_SCHEDULES
from available import REQUEST
from course import CLASS_DEF, IS_INTENSIVE  # , CANCEL


class EnvTest(ABC):
    """Test of a specific environment..."""

    def config(self, prop: str) -> str:
        """The value of the config for the environment."""
        return config(self.env).get(prop, '')

    @property
    def headers(self):
        return {
            'Accept': 'application/json',
            API_KEY: self.config('REST_API_KEY'),
        }

    @abstractmethod
    def host(self):
        pass

    @abstractmethod
    def port(self):
        pass

    @abstractmethod
    def env(self):
        pass

    @property
    def web_root(self):
        return self.config('WEB_ROOT')

    @property
    def phost(self):
        return f'{self.host}:{self.port}' if self.port else self.host

    @property
    def ping_endpt(self):
        return f'{self.phost}{self.web_root}/{PING_SFIX}'

    @property
    def cal_endpt(self):
        return f'{self.phost}{self.web_root}/{CAL_SFIX}'

    @property
    def sched_endpt(self):
        return f'{self.phost}{self.web_root}/{SCHEDULE_SFIX}'

    def test_ping(self):
        """Test basic system availability."""
        res = post(self.ping_endpt, headers=self.headers, json={})
        ddo = json.loads(res.text)
        assert len(ddo) == 2, json.dumps(ddo)
        assert SUCCESS in ddo, json.dumps(ddo)
        assert ddo[SUCCESS], json.dumps(ddo)
        assert MESSAGE in ddo, json.dumps(ddo)

    def cal_test_pos(self, tids: List[int]):
        """Test of positive calendar results."""
        # TODO: similar for negative.
        dd = {
            TEACHER_IDS: tids,
            START_TIME: str(datetime.now().date()),
            END_TIME: str((datetime.now() + timedelta(days=365)).date()),
        }

        res = post(self.cal_endpt, headers=self.headers, json=dd)
        ddo = json.loads(res.text)

        print(json.dumps(ddo, indent=2))

        assert SUCCESS in ddo
        assert RESULT in ddo
        assert len(ddo[RESULT]) == len(dd[TEACHER_IDS])
        for vals in ddo[RESULT]:
            assert vals[TEACHER_ID] in dd[TEACHER_IDS]
            assert len(vals[AVAILABLE]) > 0
            assert len(vals[AVAILABLE][OUT_DATES]) > 0
            assert len(vals[AVAILABLE][INVITES]) > 0

    def sched_testing(self, fname: str, n_scheds=-1, n_invites=-1, intensive=None):
        """Test scheduling functionality."""
        course = json.load(open(fname))
        course[N_SCHEDULES] = max(course[N_SCHEDULES], n_scheds)
        if intensive is not None:
            course[CLASS_DEF][IS_INTENSIVE] = intensive

        print()
        print(json.dumps(course, indent=2))
        print()

        res = post(self.sched_endpt, headers=self.headers, json=course)
        ddo = json.loads(res.text)
        print(json.dumps(ddo, indent=2))

        if n_scheds > 0:
            assert RESULT in ddo

        if RESULT in ddo:
            assert len(course[TEACHER_IDS]) == len(ddo[RESULT])
            # TODO: more asserts
            for te in ddo[RESULT]:
                sch = te[SCHEDULES]

                if n_scheds > 0:
                    assert len(sch) >= n_scheds

                if len(sch) > 0:
                    invites = sch[0][INVITES]
                    if n_invites > 0:
                        assert 0 < len(invites) <= n_invites
                    print(40*'-')
                    print(invites[0][REQUEST])
                    print(40*'-')
        elif DETAILS in ddo:
            print(json.dumps(ddo[DETAILS], indent=2))


class LocalTest(EnvTest, ABC):
    @property
    def host(self):
        return 'http://localhost'

    @property
    def port(self):
        return self.config('WEB_PORT')


class RemoteTest(EnvTest, ABC):
    @property
    def host(self):
        return 'https://mail.helvetiaconnect.ch'

    @property
    def port(self):
        return ''


#
# TODO: do two versions of each, intensive and not
#

class StagingTest(EnvTest, ABC):
    """Staging server functionality test."""

    @property
    def env(self):
        return STAGING

    def test_cal1(self):
        self.cal_test_pos([99449])

    def test_cal2(self):
        self.cal_test_pos([99460])

    # def test_cal2(self):
    #     self.cal_test_neg([99461])

    @pytest.mark.advanced
    def test_sa1(self):
        # 2 invites -- one for Mon, another for Fri.
        fname = 'test/data/test_schedule/br_advanced_schedule_9_week_mf_ry.json'
        self.sched_testing(fname, n_scheds=1, n_invites=2)

    @pytest.mark.regular
    def test_sr1(self):
        # 1 invite -- same time for Mon, Fri.
        fname = 'test/data/test_schedule/br_regular_scheduling_mf_ry.json'
        self.sched_testing(fname, n_scheds=1, n_invites=1)

    @pytest.mark.regular
    def test_sr2(self):
        # Two schedules -- one day or another day.
        fname = 'test/data/test_schedule/br_regular_scheduling_mf_ry_1.json'
        self.sched_testing(fname, n_scheds=2, n_invites=2)

    @pytest.mark.intensive
    def test_si1(self):
        fname = 'test/data/test_schedule/br_mon_fri_intensive_ry.json'
        self.sched_testing(fname, n_scheds=3, n_invites=1)

    @pytest.mark.intensive
    def test_si2(self):
        fname = 'test/data/test_schedule/br_mon_fri_intensive_ry_1.json'
        self.sched_testing(fname, n_scheds=3, n_invites=2)

    @pytest.mark.intensive
    def test_si3(self):
        fname = 'test/data/test_schedule/br_regular_intensive_monica_patel.json'
        self.sched_testing(fname, n_scheds=3, n_invites=1)

    @pytest.mark.intensive
    def test_si4(self):
        fname = 'test/data/test_schedule/br_regular_intensive_chris_burns.json'
        self.sched_testing(fname, n_scheds=3, n_invites=2)

    @pytest.mark.intensive
    def test_si5(self):
        fname = 'test/data/test_schedule/req1_intensive_ei_hw.json'
        self.sched_testing(fname, n_scheds=3, n_invites=3, intensive=True)

    @pytest.mark.regular
    def test_sr3(self):
        fname = 'test/data/test_schedule/req1_intensive_ei_hw.json'
        self.sched_testing(fname, n_scheds=3, n_invites=1, intensive=False)


class MockTest(EnvTest, ABC):
    """Mock server functionality test."""
    @property
    def env(self):
        return MOCK

    def test_cal1(self):
        self.cal_test_pos([1, 2, 3])

    @pytest.mark.advanced
    def test_sa1(self):
        fname = 'test/data/test_schedule/br_advanced_schedule_intensive_mon.json'
        self.sched_testing(fname)

    @pytest.mark.advanced
    def test_sa2(self):
        fname = 'test/data/test_schedule/br_advanced_schedule_4_week_mwf.json'
        self.sched_testing(fname)

    @pytest.mark.advanced
    def test_sa3(self):
        fname = 'test/data/test_schedule/br_advanced_schedule_specific_3_day.json'
        self.sched_testing(fname)

    @pytest.mark.intensive
    def test_si1(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_1_month_intense.json'
        self.sched_testing(fname)

    @pytest.mark.intensive
    def test_si2(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_3.json'
        self.sched_testing(fname)

    @pytest.mark.intensive
    def test_si3(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_5.json'
        self.sched_testing(fname)

    @pytest.mark.intensive
    def test_si4(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_6.json'
        self.sched_testing(fname)

    @pytest.mark.intensive
    def test_si5(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_only_never_in.json'
        self.sched_testing(fname)

    @pytest.mark.intensive
    def test_si6(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_short_mon_fri.json'
        self.sched_testing(fname)

    @pytest.mark.regular
    def test_sr1(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_mon_fri_2_months.json'
        self.sched_testing(fname)

    @pytest.mark.regular
    def test_sr2(self):
        fname = 'test/data/test_schedule/br_regular_scheduling_mwf.json'
        self.sched_testing(fname)


class DevTest(EnvTest, ABC):
    """Dev server functionality test."""

    @property
    def env(self):
        return DEV

    # TODO: the calls should all return the same thing -- make sure of that...


class ProdTest(EnvTest, ABC):
    @property
    def env(self):
        return PROD


class TestLocalMock(LocalTest, MockTest):
    pass


class TestRemoteMock(RemoteTest, MockTest):
    pass


class TestLocalStaging(LocalTest, StagingTest):
    pass


class TestRemoteStaging(RemoteTest, StagingTest):
    pass


class TestLocalDev(LocalTest, DevTest):
    pass


class TestRemoteDev(RemoteTest, DevTest):
    pass


class TestRemoteProd(RemoteTest, ProdTest):
    pass


class TestLocalProd(LocalTest, ProdTest):
    pass
