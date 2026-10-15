"""Add a compact contribution window to the GitHub-only website launch banner."""

from datetime import timedelta
import html
import math

try:
    from .contributions_card import COLORS, _date, _days, _month_starts, _periods
except ImportError:
    from contributions_card import COLORS, _date, _days, _month_starts, _periods


# Keep the original terminal copy, left-side coordinates and animation intact.
# This SVG is a GitHub profile entry point, not the personal website's hero.
TEMPLATE = '''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="__HEIGHT__" viewBox="0 0 1000 __HEIGHT__" role="img" aria-labelledby="title desc" xml:space="preserve">
  <title id="title">李俊祎 · LJY OS 个人网站启动终端与 GitHub 贡献记录</title>
  <desc id="desc">用终端动画介绍 AI 产品、智能体与知识库。右侧显示 __SUMMARY__。点击访问李俊祎的个人网站。</desc>
  <style>
    :root { color-scheme: light; }
    .window { fill: #f8fafb; stroke: #d8e0e7; stroke-width: 2; }
    .bar { fill: #f1f4f6; }
    .divider { stroke: #d8e0e7; stroke-width: 1; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Arial Unicode MS", "PingFang SC", "Microsoft YaHei", monospace; }
    .title { fill: #526273; font-size: 18px; font-weight: 700; }
    .meta { fill: #9aa7b3; font-size: 12px; letter-spacing: .8px; }
    .line { opacity: 0; animation: reveal 8s ease-in-out infinite; }
    .l1 { animation-delay: .15s; }
    .l2 { animation-delay: .48s; }
    .l3 { animation-delay: .81s; }
    .l4 { animation-delay: 1.14s; }
    .l5 { animation-delay: 1.47s; }
    .l6 { animation-delay: 1.80s; }
    .l7 { animation-delay: 2.13s; }
    .l8 { animation-delay: 2.46s; }
    .body { fill: #566573; font-size: 16px; }
    .prompt { fill: #3478c9; font-size: 16px; font-weight: 700; }
    .ok { fill: #4aa176; font-weight: 700; }
    .ready { fill: #3478c9; font-size: 17px; font-weight: 700; opacity: 0; animation: ready 8s ease-in-out infinite; }
    .cta { fill: #526273; font-size: 14px; letter-spacing: 1.8px; opacity: 0; animation: cta 8s ease-in-out infinite; }
    .arrow { fill: #3478c9; font-size: 22px; opacity: 0; animation: arrow 1.4s ease-in-out infinite; animation-delay: 3.9s; }
    .contrib-surface { fill: #f8fafb; stroke: #d8e0e7; stroke-width: 1; }
    .contrib-meta { fill: #718092; font-size: 11px; }
    .contrib-heading { fill: #3478c9; font-size: 16px; font-weight: 700; }
    .contrib-total { fill: #3478c9; font-size: 13px; font-weight: 700; }
    .contrib-label { fill: #566573; font-size: 12px; }
    .contrib-month, .contrib-weekday { fill: #627386; font-size: 12px; }
    @keyframes reveal {
      0%, 5% { opacity: 0; transform: translateY(5px); }
      10%, 77% { opacity: 1; transform: translateY(0); }
      88%, 100% { opacity: 0; transform: translateY(-2px); }
    }
    @keyframes ready {
      0%, 42% { opacity: 0; transform: translateY(5px); }
      48%, 82% { opacity: 1; transform: translateY(0); }
      92%, 100% { opacity: 0; }
    }
    @keyframes cta {
      0%, 50% { opacity: 0; }
      57%, 84% { opacity: 1; }
      92%, 100% { opacity: 0; }
    }
    @keyframes arrow {
      0%, 100% { opacity: .35; transform: translateX(0); }
      50% { opacity: 1; transform: translateX(7px); }
    }
    @media (prefers-reduced-motion: reduce) {
      .line, .ready, .cta, .arrow { animation: none; opacity: 1; transform: none; }
    }
  </style>

  <rect class="window" x="1" y="1" width="998" height="__WINDOW_HEIGHT__" rx="18"/>
  <path class="bar" d="M19 2h962a18 18 0 0 1 18 18v31H1V20A18 18 0 0 1 19 2z"/>
  <line class="divider" x1="1" y1="52" x2="999" y2="52"/>
  <circle cx="24" cy="27" r="7" fill="#ef6461"/>
  <circle cx="47" cy="27" r="7" fill="#efbd4e"/>
  <circle cx="70" cy="27" r="7" fill="#55b96f"/>
  <text class="mono meta" x="500" y="31" text-anchor="middle">lijunyi@ljy-mac — 17lijunyi — 100×30</text>

  <text class="mono title line l1" x="54" y="93">李俊祎 OS v2.0.0 — Clear Light</text>
  <text class="mono body line l2" x="54" y="126">[ <tspan class="ok">OK</tspan> ] Load 产品思维内核 product-thinking.ai</text>
  <text class="mono body line l3" x="54" y="157">[ <tspan class="ok">OK</tspan> ] Mount /products    AI 产品实践</text>
  <text class="mono body line l4" x="54" y="188">[ <tspan class="ok">OK</tspan> ] Mount /agents      智能体工作流</text>
  <text class="mono body line l5" x="54" y="219">[ <tspan class="ok">OK</tspan> ] Mount /knowledge   知识库</text>
  <text class="mono prompt line l6" x="54" y="267">lijunyi@ljy-mac ~ % <tspan class="body">whoami</tspan></text>
  <text class="mono body line l7" x="54" y="298">李俊祎 · AI 产品经理</text>
  <text class="mono prompt line l8" x="54" y="346">lijunyi@ljy-mac ~ % <tspan class="body">open lijunyi.os</tspan></text>
  <text class="mono ready" x="54" y="389">SYSTEM READY</text>

__PANEL__

  <text class="mono cta" x="500" y="__CTA_Y__" text-anchor="middle">点击访问个人网站 · 17lijunyi</text>
  <text class="mono arrow" x="500" y="__ARROW_Y__" text-anchor="middle">→</text>
</svg>
'''


def render_launch_svg(days, start, end):
    """Render all bounded contribution days inside the existing right-hand space.

    Rolling three-month windows stay in one continuous row across years and
    half-years. Longer explicitly requested ranges can use additional rows.
    """
    start, end = _date(start), _date(end)
    if start > end:
        raise ValueError('Contribution range start must not be after end')
    values = _days(days, start, end)
    total = sum(count for count, _ in values.values())
    periods = []
    bounds = list(_periods(start, end))
    month_y = 216 if len(bounds) > 1 else 196
    for first, last in bounds:
        sunday = first.toordinal() - (first.weekday() + 1) % 7
        weeks = (last.toordinal() - sunday) // 7 + 1
        step = min(25, 310 / weeks)
        cell = step * .8
        grid_width = (weeks - 1) * step + cell
        left = 620 + (310 - grid_width) / 2
        label_ends, labels = [], []
        for month in _month_starts(first, last):
            x = left + ((month.toordinal() - sunday) // 7) * step
            label = f'{month.month}月'
            row = next((i for i, right in enumerate(label_ends) if x >= right + 3), len(label_ends))
            if row == len(label_ends):
                label_ends.append(0)
            label_ends[row] = x + 12 * len(label)
            labels.append((month, x, label, row))
        grid_y = month_y + 13 + (len(label_ends) - 1) * 14
        periods.append((first, last, sunday, step, cell, left, month_y, grid_y, labels))
        month_y = grid_y + 6 * step + cell + 43
    last_bottom = periods[-1][7] + 6 * periods[-1][3] + periods[-1][4]
    footer_y = last_bottom + 27
    panel_bottom = footer_y + 17
    height = max(520, math.ceil(panel_bottom + 97))
    cta_y = height - 72
    panel = [
        '<g id="contributions-panel" role="img" aria-labelledby="contrib-title contrib-desc">',
        '<title id="contrib-title">GitHub 贡献记录</title>',
        f'<desc id="contrib-desc">{start} 至 {end}，累计 {total} 次贡献。每列一周，周日为第一行。</desc>',
        f'<rect class="contrib-surface" x="574" y="100" width="374" height="{panel_bottom - 100:.2f}" rx="12"/>',
        '<path class="bar" d="M587 100h348a12 12 0 0 1 12 12v16H575v-16a12 12 0 0 1 12-12z"/>',
        '<line class="divider" x1="575" y1="129" x2="947" y2="129"/>',
        '<circle cx="589" cy="115" r="3" fill="#ef6461"/>',
        '<circle cx="599" cy="115" r="3" fill="#efbd4e"/>',
        '<circle cx="609" cy="115" r="3" fill="#55b96f"/>',
        '<text class="mono contrib-meta" x="761" y="119" text-anchor="middle">contributions</text>',
        '<text class="mono contrib-heading" x="594" y="155">GitHub 贡献记录</text>',
        f'<text class="mono contrib-total" x="928" y="155" text-anchor="end">累计 {total}</text>',
        f'<text class="mono contrib-label" x="594" y="175">{start} — {end}</text>',
    ]
    for first, last, sunday, step, cell, left, label_y, grid_y, labels in periods:
        half = 1 if first.month <= 6 else 2
        panel.append(f'<g class="contrib-period" data-period="{first.year}-H{half}" data-step="{step:.4f}">')
        if len(periods) > 1:
            panel.append(f'<text class="mono contrib-meta" x="594" y="{label_y - 20:.2f}">{first.year}年 · {"上半年" if half == 1 else "下半年"}</text>')
        for month, x, label, row in labels:
            # A partial month can share a week with the next month; reserve
            # another label row before the grid instead of hiding the label.
            panel.append(f'<text class="mono contrib-month" data-month="{month.year}-{month.month:02}" x="{x:.2f}" y="{label_y + row * 14:.2f}">{label}</text>')
        for weekday, label in ((1, '一'), (3, '三'), (5, '五')):
            panel.append(f'<text class="mono contrib-weekday" x="{left - 13:.2f}" y="{grid_y + weekday * step + cell / 2 + 4:.2f}" text-anchor="end">{label}</text>')
        cursor = first
        while True:
            count, level = values.get(cursor, (0, 0))
            week, weekday = divmod(cursor.toordinal() - sunday, 7)
            label = html.escape(f'{cursor} · {count} 次贡献', quote=True)
            panel.append(f'<rect class="contrib-day" x="{left + week * step:.2f}" y="{grid_y + weekday * step:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="{min(3, cell * .16):.2f}" fill="{COLORS[level]}" data-date="{cursor}" data-count="{count}" data-level="{level}" aria-label="{label}"><title>{label}</title></rect>')
            if cursor == last:
                break
            cursor += timedelta(days=1)
        panel.append('</g>')
    panel += [
        f'<circle cx="598" cy="{footer_y - 4:.2f}" r="2.5" fill="#4aa176"/>',
        f'<text class="mono contrib-meta" x="608" y="{footer_y:.2f}">自动同步</text>',
        f'<text class="mono contrib-meta" x="809" y="{footer_y:.2f}">少</text>',
    ]
    for level, color in enumerate(COLORS):
        panel.append(f'<rect class="contrib-legend" x="{830 + level * 15}" y="{footer_y - 10:.2f}" width="11" height="11" rx="2" fill="{color}"/>')
    panel += [f'<text class="mono contrib-meta" x="919" y="{footer_y:.2f}">多</text>', '</g>']
    replacements = {
        '__HEIGHT__': str(height), '__WINDOW_HEIGHT__': str(height - 2),
        '__CTA_Y__': str(cta_y), '__ARROW_Y__': str(cta_y + 35),
        '__SUMMARY__': f'{start} 至 {end}，累计 {total} 次贡献',
        '__PANEL__': '\n'.join(panel),
    }
    svg = TEMPLATE
    for key, value in replacements.items():
        svg = svg.replace(key, value)
    return svg
