from datetime import datetime
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from schedule import execute, slots


class ScheduleTests(unittest.TestCase):
    now = datetime(2026, 11, 4, 9, tzinfo=ZoneInfo('Asia/Kolkata'))
    schedule = {'times': ['08:00', '10:00'], 'days': [2]}

    def test_local_weekly_slots(self):
        today = [d.strftime('%H:%M %z') for d in slots(self.schedule, self.now) if d.date() == self.now.date()]
        self.assertEqual(today, ['08:00 +0530', '10:00 +0530'])

    @patch('schedule.control',return_value={})
    @patch('schedule.run')
    @patch('schedule.rpc')
    def test_restart_skips_committed_slot(self, rpc, run, control):
        rpc.return_value = {'slot': '2026-11-04T08:00:00+05:30'}
        self.assertTrue(execute('public-company-sites', self.schedule, self.now))
        run.assert_not_called()

    @patch('schedule.control',return_value={})
    @patch('schedule.run')
    @patch('schedule.rpc')
    def test_empty_crawl_reports_failure(self, rpc, run, control):
        rpc.side_effect = [{}, {'status': 'failed'}]
        run.return_value = ([], {'errors': [], 'pages_fetched': 0})
        self.assertFalse(execute('public-company-sites', self.schedule, self.now))
        self.assertEqual(rpc.call_args.args[0]['action'], 'failure')
