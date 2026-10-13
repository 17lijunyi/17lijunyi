from datetime import date
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


spec = importlib.util.spec_from_file_location('contributions_card', Path(__file__).resolve().parents[1] / 'scripts/contributions_card.py')
card = importlib.util.module_from_spec(spec)
spec.loader.exec_module(card)
NS = {'svg': 'http://www.w3.org/2000/svg'}


def parsed(days, start, end):
    return ET.fromstring(card.render_svg(days, start, end))


def cells(svg):
    return {item.attrib['data-date']: item for item in svg.findall('.//svg:rect[@class="day"]', NS)}


class ContributionsCardTest(unittest.TestCase):
    def test_missing_days_fill_zero_and_total_ignores_outside_range(self):
        svg = parsed([
            {'date': '2026-07-31', 'count': 1000, 'level': 4},
            {'date': '2026-08-01', 'count': 5, 'level': 2},
            {'date': '2026-09-01', 'count': 17, 'level': 4},
            {'date': '2026-10-13', 'count': 1, 'level': 1},
            {'date': '2026-10-14', 'count': 2000, 'level': 4},
        ], '2026-08-01', '2026-10-13')
        days = cells(svg)
        self.assertEqual(len(days), 74)
        self.assertNotIn('2026-07-31', days)
        self.assertNotIn('2026-10-14', days)
        self.assertEqual(days['2026-08-02'].attrib['data-count'], '0')
        self.assertEqual(days['2026-08-02'].attrib['data-level'], '0')
        self.assertEqual(days['2026-09-01'].attrib['data-count'], '17')
        self.assertEqual(days['2026-09-01'].find('svg:title', NS).text, '2026-09-01 · 17 次贡献')
        self.assertIn('累计贡献 · 23', ''.join(svg.itertext()))
        self.assertIn('2026-08-01 — 2026-10-13', ''.join(svg.itertext()))
        group = svg.find('.//svg:g[@class="period"]', NS)
        self.assertEqual(group.attrib['data-step'], '56')
        self.assertEqual(group.attrib['data-cell'], '46')
        grid_width = max(int(day.attrib['x']) + int(day.attrib['width']) for day in days.values()) - min(int(day.attrib['x']) for day in days.values())
        self.assertGreaterEqual(grid_width, 650)
        self.assertEqual(svg.attrib['height'], '644')

    def test_sunday_is_first_row_and_saturday_closes_the_same_week(self):
        svg = parsed([], '2026-08-01', '2026-08-09')
        days = cells(svg)
        sunday = days['2026-08-02'].attrib
        monday = days['2026-08-03'].attrib
        saturday = days['2026-08-08'].attrib
        self.assertEqual(sunday['x'], monday['x'])
        self.assertEqual(sunday['x'], saturday['x'])
        step = int(svg.find('.//svg:g[@class="period"]', NS).attrib['data-step'])
        self.assertEqual(int(monday['y']) - int(sunday['y']), step)
        self.assertEqual(int(saturday['y']) - int(sunday['y']), 6 * step)
        self.assertEqual(int(days['2026-08-09'].attrib['x']) - int(sunday['x']), step)
        self.assertEqual(days['2026-08-09'].attrib['y'], sunday['y'])
        labels = [item.text for item in svg.findall('.//svg:text[@class="mono weekday"]', NS)]
        self.assertEqual(labels, list(card.WEEKDAYS))

    def test_month_labels_are_chinese_and_partial_month_labels_do_not_overlap(self):
        svg = parsed([], '2026-08-31', '2026-10-01')
        labels = svg.findall('.//svg:text[@class="mono month"]', NS)
        self.assertEqual([item.text for item in labels], ['8月', '9月', '10月'])
        self.assertEqual([item.attrib['data-month'] for item in labels], ['2026-08', '2026-09', '2026-10'])
        self.assertEqual(labels[0].attrib['x'], labels[1].attrib['x'])
        self.assertNotEqual(labels[0].attrib['y'], labels[1].attrib['y'])
        for label in labels:
            self.assertLess(int(label.attrib['y']) + 4, min(int(day.attrib['y']) for day in cells(svg).values()))

    def test_no_cells_are_created_for_blank_padding_or_future_days(self):
        svg = parsed([
            {'date': '2026-10-14', 'count': 9, 'level': 4},
            {'date': '2027-01-01', 'count': 20, 'level': 4},
        ], '2026-10-12', '2026-10-13')
        self.assertEqual(list(cells(svg)), ['2026-10-12', '2026-10-13'])
        self.assertEqual(len(svg.findall('.//svg:rect[@class="day"]', NS)), 2)
        self.assertIn('累计贡献 · 0', ''.join(svg.itertext()))

    def test_half_year_and_year_boundaries_make_bounded_separate_rows(self):
        svg = parsed([], '2026-08-01', '2028-12-31')
        periods = svg.findall('.//svg:g[@class="period"]', NS)
        self.assertEqual([group.attrib['data-period'] for group in periods], ['2026-H2', '2027-H1', '2027-H2', '2028-H1', '2028-H2'])
        self.assertEqual(svg.attrib['width'], '1000')
        days = cells(svg)
        self.assertEqual(len(days), (date(2028, 12, 31) - date(2026, 8, 1)).days + 1)
        self.assertIn('2026-12-31', days)
        self.assertIn('2027-01-01', days)
        for group in periods:
            row_cells = group.findall('svg:rect[@class="day"]', NS)
            self.assertTrue(all(0 <= int(day.attrib['x']) and int(day.attrib['x']) + int(day.attrib['width']) < 1000 for day in row_cells))
        for previous, following in zip(periods, periods[1:]):
            previous_bottom = max(int(day.attrib['y']) + int(day.attrib['height']) for day in previous.findall('svg:rect[@class="day"]', NS))
            next_heading = min(int(text.attrib['y']) for text in following.findall('svg:text', NS))
            self.assertLess(previous_bottom, next_heading)
        self.assertEqual(periods[-1].attrib['data-step'], '30')
        self.assertEqual(periods[-1].attrib['data-cell'], '25')
        last_bottom = max(int(day.attrib['y']) + int(day.attrib['height']) for day in periods[-1].findall('svg:rect[@class="day"]', NS))
        legend_top = min(int(legend.attrib['y']) for legend in svg.findall('.//svg:rect[@class="legend"]', NS))
        self.assertLess(last_bottom, legend_top)

    def test_all_five_levels_use_palette_and_legend_without_invented_counts(self):
        svg = parsed([{'date': f'2026-08-0{level + 1}', 'count': level, 'level': level} for level in range(5)],
                     '2026-08-01', '2026-08-05')
        self.assertEqual([day.attrib['fill'] for day in cells(svg).values()], list(card.COLORS))
        legends = svg.findall('.//svg:rect[@class="legend"]', NS)
        self.assertEqual([legend.attrib['fill'] for legend in legends], list(card.COLORS))
        self.assertIn('累计贡献 · 10', ''.join(svg.itertext()))
        self.assertTrue(all(text in ''.join(svg.itertext()) for text in ('少', '多')))

    def test_identical_duplicates_are_not_double_counted_and_conflicts_fail(self):
        record = {'date': '2026-08-01', 'count': 7, 'level': 2}
        svg = parsed([record, dict(record)], '2026-08-01', '2026-08-01')
        self.assertIn('累计贡献 · 7', ''.join(svg.itertext()))
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            card.render_svg([record, dict(record, count=8)], '2026-08-01', '2026-08-01')

    def test_date_objects_and_input_order_produce_identical_deterministic_output(self):
        records = [{'date': '2026-08-01', 'count': 1, 'level': 1},
                   {'date': '2026-08-02', 'count': 2, 'level': 2}]
        self.assertEqual(card.render_svg(records, date(2026, 8, 1), date(2026, 8, 2)),
                         card.render_svg(list(reversed(records)), '2026-08-01', '2026-08-02'))

    def test_malicious_metadata_is_never_interpreted_as_svg_markup(self):
        payload = '<script>alert("x")</script><image onload="x"/>'
        svg = card.render_svg([{'date': '2026-08-01', 'count': 1, 'level': 1, 'title': payload}],
                              '2026-08-01', '2026-08-01')
        self.assertNotIn(payload, svg)
        self.assertFalse(ET.fromstring(svg).findall('.//svg:script', NS))
        for field in ('date', 'count', 'level'):
            with self.subTest(field=field):
                record = {'date': '2026-08-01', 'count': 1, 'level': 1, field: payload}
                with self.assertRaises(ValueError):
                    card.render_svg([record], '2026-08-01', '2026-08-01')
        with self.assertRaises(ValueError):
            card.render_svg([], payload, '2026-08-01')

    def test_invalid_ranges_and_counts_are_rejected_and_zero_cannot_be_green(self):
        with self.assertRaises(ValueError):
            card.render_svg([], '2026-08-02', '2026-08-01')
        for value in (-1, 1.5, True, '7'):
            with self.subTest(count=value):
                with self.assertRaises(ValueError):
                    card.render_svg([{'date': '2026-08-01', 'count': value, 'level': 1}], '2026-08-01', '2026-08-01')
        svg = parsed([{'date': '2026-08-01', 'count': 0, 'level': 4}], '2026-08-01', '2026-08-01')
        self.assertEqual(cells(svg)['2026-08-01'].attrib['data-level'], '0')


if __name__ == '__main__':
    unittest.main()
