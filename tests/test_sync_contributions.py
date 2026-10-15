from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import sync_contributions as sync


def calendar(first, last, count=1):
    days = [{'date': (first + timedelta(days=i)).isoformat(), 'contributionCount': count,
             'contributionLevel': 'FIRST_QUARTILE' if count else 'NONE'}
            for i in range((last - first).days + 1)]
    return {'data': {'user': {'contributionsCollection': {'contributionCalendar': {
        'totalContributions': len(days) * count, 'weeks': [{'contributionDays': days}]}}}}}


class ContributionSyncTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.config = {'owner': 'owner', 'profile_repo': 'owner'}
        self.first, self.last = date(2026, 8, 1), date(2026, 8, 3)
        self.days = sync.parse_calendar(calendar(self.first, self.last), self.first, self.last)
        self.original = 'Personal website and social links\n' + sync.START + '\nold chart\n' + sync.END + '\nProject covers and articles\n'
        (self.root / 'README.md').write_text(self.original)

    def test_calendar_month_window_handles_month_ends_leap_year_and_year_rollover(self):
        cases = (
            ('2026-10-15', 3, '2026-07-15'),
            ('2026-05-31', 3, '2026-02-28'),
            ('2028-05-31', 3, '2028-02-29'),
            ('2027-01-31', 3, '2026-10-31'),
            ('2026-12-31', 3, '2026-09-30'),
            ('2026-11-30', 2, '2026-09-30'),
            ('2028-02-29', 12, '2027-02-28'),
        )
        for end, months, expected in cases:
            with self.subTest(end=end, months=months):
                self.assertEqual(sync.rolling_start(date.fromisoformat(end), months),
                                 date.fromisoformat(expected))
        for months in (0, 13, -1, 3.0, True, '3', None):
            with self.subTest(months=months), self.assertRaises(ValueError):
                sync.rolling_start(date(2026, 10, 15), months)

    def test_main_uses_through_date_and_configured_months_for_saved_data(self):
        real_update = sync.update
        for through, months, first in (
            ('2026-10-15', 3, '2026-07-15'),
            ('2027-01-31', 3, '2026-10-31'),
            ('2026-11-30', 2, '2026-09-30'),
        ):
            with self.subTest(through=through, months=months):
                start, end = date.fromisoformat(first), date.fromisoformat(through)
                config = dict(self.config, rolling_months=months, timezone='Asia/Shanghai')
                (self.root / 'contributions.json').write_text(json.dumps(config))
                days = [{'date': (start + timedelta(days=i)).isoformat(), 'count': 1, 'level': 1}
                        for i in range((end - start).days + 1)]
                fixture = self.root / 'calendar.json'
                fixture.write_text(json.dumps({'days': [
                    {'date': (start - timedelta(days=1)).isoformat(), 'count': 1000, 'level': 4},
                    *days,
                    {'date': (end + timedelta(days=1)).isoformat(), 'count': 1000, 'level': 4},
                ]}))
                def update_in_temporary_repo(config, days, first, last):
                    return real_update(config, days, first, last, root=self.root)
                with patch.object(sync, 'ROOT', self.root), \
                        patch.object(sync, 'update', side_effect=update_in_temporary_repo), \
                        patch.object(sync, 'github_token') as token, \
                        patch('sys.argv', ['sync_contributions.py', '--through', through,
                                           '--data-json', str(fixture)]), patch('builtins.print'):
                    sync.main()
                token.assert_not_called()
                output = json.loads((self.root / 'assets/contributions-data.json').read_text())
                self.assertEqual((output['start_date'], output['end_date']), (first, through))
                self.assertEqual(output['days'], days)
                self.assertEqual(output['total'], len(days))
                self.assertIn(f'{first} 至 {through}', (self.root / 'README.md').read_text())

    def test_fetch_splits_at_year_boundary_without_duplicate_days(self):
        requests = []
        def request(variables, token):
            self.assertEqual(token, 'fixture-token')
            requests.append(variables)
            first, last = date.fromisoformat(variables['from'][:10]), date.fromisoformat(variables['to'][:10])
            return calendar(first, last)
        days = sync.fetch_days('owner', date(2026, 12, 30), date(2027, 1, 2), 'fixture-token', request=request)
        self.assertEqual(len(days), 4)
        self.assertEqual(sum(day['count'] for day in days), 4)
        self.assertEqual([(item['from'], item['to']) for item in requests], [
            ('2026-12-30T00:00:00Z', '2026-12-31T23:59:59Z'),
            ('2027-01-01T00:00:00Z', '2027-01-02T23:59:59Z')])
        self.assertEqual(list(sync.year_ranges(date(2026, 8, 1), date(2028, 2, 29))), [
            (date(2026, 8, 1), date(2026, 12, 31)),
            (date(2027, 1, 1), date(2027, 12, 31)),
            (date(2028, 1, 1), date(2028, 2, 29))])

    def test_api_errors_incomplete_dates_and_bad_totals_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'query failed'):
            sync.parse_calendar({'errors': [{'message': 'unavailable'}]}, self.first, self.last)
        payload = calendar(self.first, self.last)
        payload['data']['user']['contributionsCollection']['contributionCalendar']['weeks'][0]['contributionDays'].pop()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            sync.parse_calendar(payload, self.first, self.last)
        payload = calendar(self.first, self.last)
        payload['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions'] = 99
        with self.assertRaisesRegex(ValueError, 'does not match'):
            sync.parse_calendar(payload, self.first, self.last)

    def test_incomplete_calendar_does_not_overwrite_previous_image_or_readme(self):
        (self.root / 'assets').mkdir()
        (self.root / 'assets/contributions.svg').write_text('last successful image')
        (self.root / 'assets/portfolio-launch.svg').write_text('last successful launch image')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            sync.update(self.config, self.days[:-1], self.first, self.last, self.root)
        self.assertEqual((self.root / 'README.md').read_text(), self.original)
        self.assertEqual((self.root / 'assets/contributions.svg').read_text(), 'last successful image')
        self.assertEqual((self.root / 'assets/portfolio-launch.svg').read_text(), 'last successful launch image')

    def test_sync_only_replaces_chart_and_invalidates_cache_when_data_changes(self):
        changed = sync.update(self.config, self.days, self.first, self.last, self.root)
        self.assertEqual(set(changed), {'README.md', 'assets/portfolio-launch.svg', 'assets/contributions.svg', 'assets/contributions-data.json'})
        text = (self.root / 'README.md').read_text()
        self.assertTrue(text.startswith(self.original.split(sync.START)[0]))
        self.assertTrue(text.endswith(self.original.split(sync.END)[1]))
        self.assertIn('共 3 次贡献', text)
        self.assertIn('个人网站启动终端与贡献记录', text)
        self.assertIn('href="https://owner.github.io/"', text)
        self.assertIn('<img width="1000"', text)
        self.assertEqual(text.count('<img '), 1)
        self.assertEqual(text.count('assets/portfolio-launch.svg?v='), 1)
        launch = (self.root / 'assets/portfolio-launch.svg').read_bytes()
        version = hashlib.sha256(launch).hexdigest()[:12]
        self.assertIn(f'portfolio-launch.svg?v={version}', text)
        self.assertNotIn('contributions.svg?v=', text)
        self.assertEqual(json.loads((self.root / 'assets/contributions-data.json').read_text())['total'], 3)
        self.assertEqual(sync.update(self.config, self.days, self.first, self.last, self.root), [])
        new = deepcopy(self.days)
        new[-1].update(count=7, level=3)
        sync.update(self.config, new, self.first, self.last, self.root)
        updated = (self.root / 'README.md').read_text()
        self.assertNotEqual(updated, text)
        self.assertIn('共 9 次贡献', updated)
        changed_version = hashlib.sha256((self.root / 'assets/portfolio-launch.svg').read_bytes()).hexdigest()[:12]
        self.assertNotEqual(changed_version, version)
        self.assertIn(f'portfolio-launch.svg?v={changed_version}', updated)

    def test_deleted_or_duplicate_block_is_not_recreated_or_published(self):
        for text in ('profile without chart', self.original + sync.START + sync.END):
            with self.subTest(text=text):
                (self.root / 'README.md').write_text(text)
                with self.assertRaisesRegex(ValueError, 'CONTRIBUTIONS block'):
                    sync.update(self.config, self.days, self.first, self.last, self.root)
                self.assertEqual((self.root / 'README.md').read_text(), text)
                self.assertFalse((self.root / 'assets/contributions.svg').exists())
                self.assertFalse((self.root / 'assets/portfolio-launch.svg').exists())


if __name__ == '__main__':
    unittest.main()
