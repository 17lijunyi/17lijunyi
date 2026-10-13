"""Render a bounded, deterministic GitHub contribution calendar as native SVG."""

from datetime import date, timedelta
import html
import re


WIDTH = 1000
MAX_STEP = 56
GRID_MAX_WIDTH = 840
FIRST_PERIOD_Y = 142
COLORS = ('#e2e8e9', '#c4e5cb', '#8dcc9d', '#4eaa71', '#277e4b')
WEEKDAYS = ('日', '一', '二', '三', '四', '五', '六')


def _date(value):
    if isinstance(value, date):
        return date(value.year, value.month, value.day)
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Dates must be date objects or YYYY-MM-DD strings')
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError('Dates must be valid YYYY-MM-DD calendar dates') from error


def _days(days, start, end):
    result = {}
    for entry in days:
        if not isinstance(entry, dict) or 'date' not in entry:
            raise ValueError('Each contribution day must contain date, count and level')
        day = _date(entry['date'])
        if not start <= day <= end:
            continue
        count, level = entry.get('count'), entry.get('level')
        if type(count) is not int or count < 0:
            raise ValueError('Contribution counts must be nonnegative integers')
        if type(level) is not int or not 0 <= level <= 4:
            raise ValueError('Contribution levels must be integers between 0 and 4')
        # A missing contribution cannot acquire a green activity cell.
        value = (count, level if count else 0)
        if day in result and result[day] != value:
            raise ValueError(f'Conflicting contribution records for {day.isoformat()}')
        result[day] = value
    return result


def _periods(start, end):
    """Clip calendar half-years to the requested inclusive date range."""
    cursor = start
    while True:
        last = date(cursor.year, 6, 30) if cursor.month <= 6 else date(cursor.year, 12, 31)
        last = min(last, end)
        yield cursor, last
        if last == end:
            return
        cursor = last + timedelta(days=1)


def _month_starts(start, end):
    cursor = start
    while cursor <= end:
        yield cursor
        if cursor.month == 12:
            if cursor.year == 9999:
                return
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def render_svg(days, start, end):
    """Render date/count/level records; both bounds are inclusive and explicit.

    Dates accept datetime.date or strict ISO strings. Missing dates have count 0;
    dates outside the bounds and extra metadata are ignored. No current-time or
    update timestamp is included, so unchanged data produces identical SVG.
    """
    start, end = _date(start), _date(end)
    if start > end:
        raise ValueError('Contribution range start must not be after end')
    values = _days(days, start, end)
    periods = []
    top = FIRST_PERIOD_Y
    for first, last in _periods(start, end):
        # An ordinal week anchor also supports the first year without trying to
        # construct an out-of-range Sunday in the preceding year.
        sunday = first.toordinal() - (first.weekday() + 1) % 7
        weeks = (last.toordinal() - sunday) // 7 + 1
        step = min(MAX_STEP, GRID_MAX_WIDTH // weeks)
        cell = round(step * .82)
        grid_width = (weeks - 1) * step + cell
        periods.append((first, last, sunday, step, cell, (WIDTH - grid_width) // 2, top))
        top += 100 + 6 * step + cell
    total = sum(count for count, _ in values.values())
    height = top + 20
    esc = html.escape
    span = f'{start.isoformat()} — {end.isoformat()}'
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">李俊祎 · GitHub 贡献记录</title>',
        f'<desc id="desc">{esc(span)}，累计 {total} 次贡献。按 UTC 日期显示，每列一周，周日为第一行；空白处不代表贡献日期。</desc>',
        '<style>',
        ':root { color-scheme: light; }',
        '.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Arial Unicode MS", "PingFang SC", "Microsoft YaHei", monospace; }',
        '.window { fill: #f8fafc; stroke: #d8e0e7; stroke-width: 2; }',
        '.bar { fill: #f1f4f6; }',
        '.divider { stroke: #d8e0e7; stroke-width: 1; }',
        '.heading { fill: #3478c9; font-size: 23px; font-weight: 700; }',
        '.body { fill: #566573; font-size: 14px; }',
        '.meta { fill: #9aa7b3; font-size: 12px; letter-spacing: .8px; }',
        '.month { fill: #526273; font-size: 13px; }',
        '.weekday { fill: #9aa7b3; font-size: 12px; }',
        '.day { stroke: #cbd5e1; stroke-width: .55; }',
        '</style>',
        f'<rect class="window" x="1" y="1" width="{WIDTH - 2}" height="{height - 2}" rx="18"/>',
        f'<path class="bar" d="M19 2h{WIDTH - 38}a18 18 0 0 1 18 18v27H1V20A18 18 0 0 1 19 2z"/>',
        f'<line class="divider" x1="1" y1="48" x2="{WIDTH - 1}" y2="48"/>',
        '<circle cx="24" cy="25" r="7" fill="#ef6461"/>',
        '<circle cx="47" cy="25" r="7" fill="#efbd4e"/>',
        '<circle cx="70" cy="25" r="7" fill="#55b96f"/>',
        f'<text class="mono meta" x="{WIDTH // 2}" y="29" text-anchor="middle">lijunyi@ljy-mac — contributions</text>',
        '<text class="mono heading" x="54" y="87">GitHub 贡献记录</text>',
        f'<text class="mono heading" x="{WIDTH - 54}" y="87" text-anchor="end">累计贡献 · {total}</text>',
        f'<text class="mono body" x="54" y="111">{esc(span)}</text>',
    ]
    for first, last, sunday, step, cell, left, top in periods:
        grid_y = top + 58
        half = 1 if first.month <= 6 else 2
        label = f'{first.year}年 · {"上半年" if half == 1 else "下半年"}'
        parts += [f'<g class="period" data-period="{first.year}-H{half}" data-step="{step}" data-cell="{cell}">',
                  f'<text class="mono body" x="54" y="{top}">{esc(label)}</text>',
                  f'<text class="mono body" x="{WIDTH - 54}" y="{top}" text-anchor="end">{first.month}月{first.day}日 — {last.month}月{last.day}日</text>']
        # A short first month can share a week with the next month. Use a second
        # label row when necessary rather than overlap or hide either month.
        label_ends = []
        for month_start in _month_starts(first, last):
            x = left + ((month_start.toordinal() - sunday) // 7) * step
            text = f'{month_start.month}月'
            label_width = 13 * len(text)
            row = next((i for i, right in enumerate(label_ends) if x >= right + 4), len(label_ends))
            if row == len(label_ends):
                label_ends.append(0)
            label_ends[row] = x + label_width
            parts.append(f'<text class="mono month" data-month="{month_start.year}-{month_start.month:02}" x="{x}" y="{top + 24 + row * 16}">{esc(text)}</text>')
        for weekday, text in enumerate(WEEKDAYS):
            parts.append(f'<text class="mono weekday" x="{left - 17}" y="{grid_y + weekday * step + cell // 2 + 4}" text-anchor="end">{text}</text>')
        cursor = first
        while True:
            count, level = values.get(cursor, (0, 0))
            week, weekday = divmod(cursor.toordinal() - sunday, 7)
            day = cursor.isoformat()
            title = f'{day} · {count} 次贡献'
            parts.append(f'<rect class="day" x="{left + week * step}" y="{grid_y + weekday * step}" width="{cell}" height="{cell}" rx="4" fill="{COLORS[level]}" data-date="{day}" data-count="{count}" data-level="{level}" aria-label="{esc(title, quote=True)}"><title>{esc(title)}</title></rect>')
            if cursor == last:
                break
            cursor += timedelta(days=1)
        parts.append('</g>')
    footer_y = height - 27
    parts += [f'<text class="mono body" x="54" y="{footer_y}">GitHub 贡献记录（UTC 日期）</text>',
              f'<text class="mono body" x="{WIDTH - 218}" y="{footer_y}">少</text>']
    for level, color in enumerate(COLORS):
        parts.append(f'<rect class="legend" x="{WIDTH - 190 + level * 22}" y="{footer_y - 13}" width="16" height="16" rx="3" fill="{color}" data-level="{level}"/>')
    parts += [f'<text class="mono body" x="{WIDTH - 66}" y="{footer_y}">多</text>', '</svg>']
    return '\n'.join(parts) + '\n'
