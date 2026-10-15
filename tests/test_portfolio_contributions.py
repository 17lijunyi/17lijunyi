from datetime import date, timedelta
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from scripts.portfolio_launch import render_launch_svg


NS = {'svg': 'http://www.w3.org/2000/svg'}


class PortfolioContributionTest(unittest.TestCase):
    def test_real_calendar_is_embedded_once_with_original_terminal(self):
        data = json.loads((Path(__file__).resolve().parents[1] / 'assets/contributions-data.json').read_text())
        svg = ET.fromstring(render_launch_svg(data['days'], data['start_date'], data['end_date']))
        panels = svg.findall('.//svg:g[@id="contributions-panel"]', NS)
        self.assertEqual(len(panels), 1)
        cells = panels[0].findall('.//svg:rect[@class="contrib-day"]', NS)
        self.assertEqual([cell.attrib['data-date'] for cell in cells], [day['date'] for day in data['days']])
        self.assertEqual(sum(int(cell.attrib['data-count']) for cell in cells), data['total'])
        self.assertEqual(cells[0].attrib['data-date'], data['start_date'])
        boot = ''.join(svg.itertext())
        for text in ('李俊祎 OS v2.0.0 — Clear Light', 'product-thinking.ai', 'open lijunyi.os', 'SYSTEM READY'):
            self.assertIn(text, boot)
        self.assertEqual(len(svg.findall('.//svg:text[@class="mono cta"]', NS)), 1)

    def test_padding_is_blank_and_zero_counts_cannot_be_green(self):
        svg = ET.fromstring(render_launch_svg([
            {'date': '2026-07-31', 'count': 50, 'level': 4},
            {'date': '2026-08-01', 'count': 0, 'level': 4},
            {'date': '2026-08-02', 'count': 3, 'level': 2},
            {'date': '2026-08-03', 'count': 50, 'level': 4},
        ], '2026-08-01', '2026-08-02'))
        cells = svg.findall('.//svg:rect[@class="contrib-day"]', NS)
        self.assertEqual([cell.attrib['data-date'] for cell in cells], ['2026-08-01', '2026-08-02'])
        self.assertEqual(cells[0].attrib['data-level'], '0')
        self.assertEqual(cells[1].attrib['data-level'], '2')
        self.assertGreater(float(cells[0].attrib['y']), float(cells[1].attrib['y']))
        self.assertLess(float(cells[0].attrib['x']), float(cells[1].attrib['x']))
        self.assertIn('累计 3', ''.join(svg.itertext()))

    def test_future_half_years_keep_history_inside_window_and_clear_cta(self):
        first, last = date(2026, 8, 1), date(2028, 7, 1)
        svg = ET.fromstring(render_launch_svg([], first, last))
        cells = svg.findall('.//svg:rect[@class="contrib-day"]', NS)
        self.assertEqual(len(cells), (last - first).days + 1)
        surface = svg.find('.//svg:rect[@class="contrib-surface"]', NS).attrib
        bottom = float(surface['y']) + float(surface['height'])
        for cell in cells:
            attr = cell.attrib
            self.assertGreaterEqual(float(attr['x']), float(surface['x']))
            self.assertLess(float(attr['x']) + float(attr['width']), float(surface['x']) + float(surface['width']))
            self.assertLess(float(attr['y']) + float(attr['height']), bottom)
        cta = svg.find('.//svg:text[@class="mono cta"]', NS)
        self.assertGreater(float(cta.attrib['y']), bottom)
        self.assertLess(float(cta.attrib['y']) + 35, float(svg.attrib['height']))
        periods = svg.findall('.//svg:g[@class="contrib-period"]', NS)
        for previous, following in zip(periods, periods[1:]):
            previous_bottom = max(float(c.attrib['y']) + float(c.attrib['height']) for c in previous.findall('svg:rect', NS))
            next_label_top = min(float(t.attrib['y']) - 12 for t in following.findall('svg:text', NS))
            self.assertLess(previous_bottom, next_label_top)

    def test_rolling_window_is_continuous_across_half_year_and_year_boundaries(self):
        for first, last in (
            ('2026-07-15', '2026-10-15'),
            ('2026-04-15', '2026-07-15'),
            ('2026-10-15', '2027-01-15'),
            ('2026-11-30', '2027-02-28'),
            ('2028-02-29', '2028-05-31'),
        ):
            with self.subTest(first=first, last=last):
                start, end = date.fromisoformat(first), date.fromisoformat(last)
                svg = ET.fromstring(render_launch_svg([
                    {'date': (start - timedelta(days=1)).isoformat(), 'count': 1000, 'level': 4},
                    {'date': first, 'count': 2, 'level': 1},
                    {'date': last, 'count': 3, 'level': 2},
                    {'date': (end + timedelta(days=1)).isoformat(), 'count': 1000, 'level': 4},
                ], first, last))
                self.assertEqual(len(svg.findall('.//svg:g[@class="contrib-period"]', NS)), 1)
                cells = svg.findall('.//svg:rect[@class="contrib-day"]', NS)
                expected = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
                self.assertEqual([cell.attrib['data-date'] for cell in cells], expected)
                self.assertEqual(sum(int(cell.attrib['data-count']) for cell in cells), 5)
                self.assertIn('累计 5', ''.join(svg.itertext()))
                surface = svg.find('.//svg:rect[@class="contrib-surface"]', NS).attrib
                bottom = float(surface['y']) + float(surface['height'])
                for cell in cells:
                    attr = cell.attrib
                    self.assertGreater(float(attr['x']), float(surface['x']))
                    self.assertLess(float(attr['x']) + float(attr['width']), float(surface['x']) + float(surface['width']))
                    self.assertLess(float(attr['y']) + float(attr['height']), bottom)
                cta = svg.find('.//svg:text[@class="mono cta"]', NS)
                self.assertGreater(float(cta.attrib['y']) - 14, bottom)
                self.assertLess(float(cta.attrib['y']) + 35, float(svg.attrib['height']))

    def test_partial_month_labels_do_not_overlap_each_other_or_cells(self):
        svg = ET.fromstring(render_launch_svg([], '2026-08-31', '2026-10-01'))
        labels = svg.findall('.//svg:text[@class="mono contrib-month"]', NS)
        self.assertEqual([label.text for label in labels], ['8月', '9月', '10月'])
        self.assertNotEqual(labels[0].attrib['y'], labels[1].attrib['y'])
        grid_top = min(float(c.attrib['y']) for c in svg.findall('.//svg:rect[@class="contrib-day"]', NS))
        self.assertTrue(all(float(label.attrib['y']) + 3 < grid_top for label in labels))


if __name__ == '__main__':
    unittest.main()
