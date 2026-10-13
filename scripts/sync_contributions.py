#!/usr/bin/env python3
"""Sync GitHub's real contribution calendar into the profile's SVG card."""
import argparse
from datetime import date, datetime, timedelta
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

try:
    from .contributions_card import render_svg
except ImportError:
    from contributions_card import render_svg

try:
    from .portfolio_launch import render_launch_svg
except ImportError:
    from portfolio_launch import render_launch_svg

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- CONTRIBUTIONS:START -->'
END = '<!-- CONTRIBUTIONS:END -->'
LEVELS = {name: index for index, name in enumerate(
    ('NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE'))}
QUERY = '''query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}'''


def year_ranges(start, end):
    if start > end:
        raise ValueError('Contribution start date is after the end date')
    while start <= end:
        stop = min(end, date(start.year, 12, 31))
        yield start, stop
        start = stop + timedelta(days=1)


def validate_days(days, start, end):
    """Reject incomplete/invalid API data instead of showing invented zero days."""
    normalized = {}
    for item in days:
        current = date.fromisoformat(item['date'])
        if not start <= current <= end:
            continue
        count, level = item['count'], item['level']
        if type(count) is not int or count < 0 or type(level) is not int or not 0 <= level <= 4:
            raise ValueError(f'Invalid contribution count or level on {current}')
        if current in normalized:
            raise ValueError(f'Duplicate contribution date: {current}')
        normalized[current] = {'date': current.isoformat(), 'count': count, 'level': level}
    expected = {start + timedelta(days=i) for i in range((end - start).days + 1)}
    if set(normalized) != expected:
        raise ValueError('Contribution calendar is incomplete; keeping the previous card')
    return [normalized[current] for current in sorted(normalized)]


def parse_calendar(payload, start, end):
    if payload.get('errors'):
        messages = '; '.join(error.get('message', 'GraphQL error') for error in payload['errors'])
        raise ValueError(f'GitHub contribution query failed: {messages}')
    try:
        calendar = payload['data']['user']['contributionsCollection']['contributionCalendar']
        days = [{'date': day['date'], 'count': day['contributionCount'],
                 'level': LEVELS[day['contributionLevel']]}
                for week in calendar['weeks'] for day in week['contributionDays']]
        days = validate_days(days, start, end)
        if sum(day['count'] for day in days) != calendar['totalContributions']:
            raise ValueError('GitHub calendar total does not match its day counts')
        return days
    except (KeyError, TypeError) as error:
        raise ValueError('Invalid GitHub contribution calendar; keeping the previous card') from error


def graphql(variables, token):
    # gh uses the platform's trusted certificates and is included on Actions runners.
    environment = dict(os.environ, GH_TOKEN=token)
    environment.pop('GH_DEBUG', None)
    response = subprocess.run(['gh', 'api', 'graphql', '--input', '-'],
                              input=json.dumps({'query': QUERY, 'variables': variables}),
                              text=True, capture_output=True, timeout=30, env=environment)
    if response.returncode:
        raise ValueError(f'GitHub contribution request failed: {response.stderr.strip()}')
    return json.loads(response.stdout)


def fetch_days(owner, start, end, token, request=graphql):
    days = []
    # GitHub collections have a one-year range; no overlapping annual requests.
    for first, last in year_ranges(start, end):
        payload = request({'login': owner, 'from': f'{first}T00:00:00Z',
                           'to': f'{last}T23:59:59Z'}, token)
        days.extend(parse_calendar(payload, first, last))
    return validate_days(days, start, end)


def github_token():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    try:
        return subprocess.check_output(['gh', 'auth', 'token'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError('Set GH_TOKEN or sign in with gh; no contribution data was changed') from error


def update(config, days, start, end, root=ROOT):
    days = validate_days(days, start, end)
    readme_path = root / 'README.md'
    readme = readme_path.read_text()
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) >= readme.index(END):
        raise ValueError('Expected one existing CONTRIBUTIONS block; keeping the previous card')
    owner, repo = config['owner'], config['profile_repo']
    if not re.fullmatch(r'[A-Za-z0-9-]+', owner) or not re.fullmatch(r'[A-Za-z0-9._-]+', repo):
        raise ValueError('Invalid GitHub account or repository name')
    total = sum(day['count'] for day in days)
    svg = render_svg(days, start, end).rstrip() + '\n'
    launch_svg = render_launch_svg(days, start, end).rstrip() + '\n'
    version = hashlib.sha256(launch_svg.encode()).hexdigest()[:12]
    src = f'https://raw.githubusercontent.com/{owner}/{repo}/main/assets/portfolio-launch.svg?v={version}'
    alt = f'个人网站启动终端与贡献记录：{start} 至 {end}，共 {total} 次贡献'
    markup = (f'<p align="center">\n  <a href="https://{owner}.github.io/">'
              f'<img width="1000" src="{src}" alt="{html.escape(alt, quote=True)}"></a>\n</p>')
    before, remaining = readme.split(START)
    _, after = remaining.split(END)
    updated = before + START + '\n' + markup + '\n' + END + after
    data = {'owner': owner, 'start_date': start.isoformat(), 'end_date': end.isoformat(),
            'total': total, 'source': 'GitHub GraphQL contributionCalendar', 'days': days}
    outputs = {'assets/contributions.svg': svg,
               'assets/portfolio-launch.svg': launch_svg,
               'assets/contributions-data.json': json.dumps(data, ensure_ascii=False, indent=2) + '\n',
               'README.md': updated}
    changed = []
    for name, content in outputs.items():
        target = root / name
        if not target.exists() or target.read_text() != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            changed.append(name)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-json', type=Path, help='Use a saved GraphQL response or normalized days offline')
    parser.add_argument('--through', help='Inclusive end date; defaults to today in the configured timezone')
    args = parser.parse_args()
    config = json.loads((ROOT / 'contributions.json').read_text())
    first = date.fromisoformat(config['start_date'])
    last = date.fromisoformat(args.through) if args.through else datetime.now(ZoneInfo(config['timezone'])).date()
    if first > last:
        raise ValueError('Contribution start date is after the end date')
    if args.data_json:
        payload = json.loads(args.data_json.read_text())
        days = parse_calendar(payload, first, last) if 'data' in payload or 'errors' in payload else validate_days(payload['days'], first, last)
    else:
        days = fetch_days(config['owner'], first, last, github_token())
    changed = update(config, days, first, last)
    print(f'{first} → {last}: {sum(day["count"] for day in days)} contributions; '
          + ('updated ' + ', '.join(changed) if changed else 'card already up to date'))


if __name__ == '__main__':
    main()
