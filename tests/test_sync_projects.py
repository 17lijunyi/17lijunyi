import copy
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('sync_projects', Path(__file__).resolve().parents[1] / 'scripts/sync_projects.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def repo(name, **kw):
    return dict(name=name, owner={'login': 'owner'}, private=False, fork=False, archived=False,
                description='A project', language='Python', stargazers_count=7, forks_count=2,
                updated_at='2026-09-01T00:00:00Z', **kw)


class ProjectCardsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.config = dict(owner='owner', profile_repo='owner', limit=6, exclude=['owner', 'owner.github.io'],
                           featured=['repo:priority'], overrides={})
        self.readme = 'Personal website\n' + sync.START + '\nold cards\n' + sync.END + '\nArticles remain here\n'
        (self.root / 'README.md').write_text(self.readme)

    def cover(self, name='priority.png'):
        path = self.root / 'assets/project-covers' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0ioAAAAASUVORK5CYII='))
        return path

    def test_selects_priority_then_recent_and_excludes_nonpublic_forks_archives(self):
        items = [repo('priority')]
        for i in range(1, 9):
            r = repo('new-' + str(i)); r['updated_at'] = f'2026-09-{i + 1:02}T00:00:00Z'; items.append(r)
        for name, flag in [('private', 'private'), ('fork', 'fork'), ('archived', 'archived')]:
            r = repo(name); r[flag] = True; items.append(r)
        items += [repo('owner'), repo('owner.github.io')]
        foreign = repo('foreign'); foreign['owner']['login'] = 'someone-else'; items.append(foreign)
        projects = sync.collect_projects(self.config, items, self.root)
        self.assertEqual(len(projects), 9)
        self.assertEqual([p['id'] for p in projects[:3]], ['repo:priority', 'repo:new-8', 'repo:new-7'])
        sync.generate(self.config, projects, self.root)
        readme = (self.root / 'README.md').read_text()
        self.assertEqual(readme.count('<picture>'), 6)
        self.assertIn('new-1', (self.root / 'PROJECTS.md').read_text())
        self.assertTrue(readme.startswith('Personal website\n'))
        self.assertTrue(readme.endswith('\nArticles remain here\n'))

    def test_live_counts_and_metadata_escape(self):
        r = repo('project'); r['description'] = '<script>alert("x")</script> & 中文描述'; r['stargazers_count'] = 123
        p = sync.collect_projects(self.config, [r], self.root)[0]
        p['title'] = '标题 <script> & "quotes"'
        for dark in [False, True]:
            markup = sync.svg_card(p, dark)
            parsed = ET.fromstring(markup)
            self.assertFalse(parsed.findall('.//{http://www.w3.org/2000/svg}script'))
            self.assertIn('123', ''.join(parsed.itertext()))
            self.assertIn(r['description'], ''.join(parsed.itertext()))

    def test_long_metadata_is_bounded(self):
        lines = sync.wrap('很长的中文标题<>&' * 100 + 'W' * 200, 40, 3)
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[-1].endswith('…'))
        self.assertTrue(all(sync.units(line) <= 40 for line in lines))

    def test_skills_get_no_inherited_statistics(self):
        folder = self.root / 'skills/example/agents'; folder.mkdir(parents=True)
        (folder.parent / 'SKILL.md').write_text('not executed')
        (folder / 'openai.yaml').write_text('interface:\n  display_name: "测试技能"\n  short_description: "测试介绍"\n')
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            p = sync.collect_projects(self.config, [], self.root)[0]
        self.assertEqual(p['id'], 'skill:example')
        self.assertNotIn('stars', p)
        self.assertIn('技能目录', sync.svg_card(p))

    def test_custom_cover_keeps_two_column_layout_links_and_svg_fallback(self):
        cover = self.cover()
        self.config['overrides']['repo:priority'] = {'cover': 'assets/project-covers/priority.png'}
        projects = sync.collect_projects(self.config, [repo('priority')] + [repo(f'other-{i}') for i in range(5)], self.root)
        self.assertEqual(projects[0]['cover'], 'assets/project-covers/priority.png')
        sync.generate(self.config, projects, self.root)
        readme = (self.root / 'README.md').read_text()
        rows = re.findall(r'<p>\n(.*?)\n</p>', readme, re.S)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.count('<img width="49%"') == 2 for row in rows))
        self.assertIn('<a href="https://github.com/owner/priority"><picture><img', rows[0])
        self.assertIn('alt="priority：A project"', rows[0])
        digest = hashlib.sha256(cover.read_bytes()).hexdigest()[:12]
        self.assertIn(f'https://raw.githubusercontent.com/owner/owner/main/assets/project-covers/priority.png?v={digest}', rows[0])
        self.assertEqual(readme.count('<source media="(prefers-color-scheme: dark)"'), 5)
        self.assertEqual(len(list((self.root / 'assets/projects').glob('*.svg'))), 10)
        self.assertTrue(readme.endswith('\nArticles remain here\n'))

    def test_cover_cache_version_tracks_image_bytes_instead_of_metadata(self):
        cover = self.cover()
        self.config['overrides']['repo:priority'] = {'cover': 'assets/project-covers/priority.png'}
        projects = sync.collect_projects(self.config, [repo('priority')], self.root)
        sync.generate(self.config, projects, self.root)
        first = re.search(r'<img width="49%" src="([^"]+)"', (self.root / 'README.md').read_text()).group(1)
        projects[0]['description'] = 'Updated metadata'
        sync.generate(self.config, projects, self.root)
        second = re.search(r'<img width="49%" src="([^"]+)"', (self.root / 'README.md').read_text()).group(1)
        self.assertEqual(first, second)
        cover.write_bytes(cover.read_bytes() + b'updated image')
        sync.generate(self.config, projects, self.root)
        third = re.search(r'<img width="49%" src="([^"]+)"', (self.root / 'README.md').read_text()).group(1)
        self.assertNotEqual(first, third)
        self.assertTrue(third.endswith(hashlib.sha256(cover.read_bytes()).hexdigest()[:12]))

    def test_skill_cover_override_uses_same_accessible_image_rendering(self):
        folder = self.root / 'skills/example/agents'; folder.mkdir(parents=True)
        (folder.parent / 'SKILL.md').write_text('not executed')
        (folder / 'openai.yaml').write_text('interface:\n  display_name: "测试技能"\n  short_description: "测试介绍"\n')
        self.cover('skill.png')
        self.config['overrides']['skill:example'] = {'cover': 'assets/project-covers/skill.png'}
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            projects = sync.collect_projects(self.config, [], self.root)
        sync.generate(self.config, projects, self.root)
        readme = (self.root / 'README.md').read_text()
        self.assertIn('<a href="https://github.com/owner/owner/tree/main/skills/example">', readme)
        self.assertIn('alt="测试技能：测试介绍"', readme)
        self.assertNotIn('<source', readme)

    def test_missing_cover_preserves_all_previous_generated_files(self):
        projects = sync.collect_projects(self.config, [repo('priority'), repo('other')], self.root)
        sync.generate(self.config, projects, self.root)
        self.cover()
        projects[0]['cover'] = 'assets/project-covers/priority.png'
        projects[1]['cover'] = 'assets/project-covers/missing.png'
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError, 'missing or outside'):
            sync.generate(self.config, projects, self.root)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_invalid_cover_paths_and_symlinks_cannot_escape_cover_directory(self):
        self.cover()
        projects = sync.collect_projects(self.config, [repo('priority')], self.root)
        covers = ['', None, 123, '/tmp/cover.png', '../cover.png', 'assets/projects/cover.png',
                  'assets/project-covers/../cover.png', 'assets/project-covers/./priority.png',
                  'assets/project-covers//priority.png', 'assets/project-covers/priority.svg',
                  'assets\\project-covers\\priority.png']
        outside = self.root / 'outside.png'
        outside.write_bytes(b'outside')
        (self.root / 'assets/project-covers/escape.png').symlink_to(outside)
        covers.append('assets/project-covers/escape.png')
        for cover in covers:
            with self.subTest(cover=cover):
                projects[0]['cover'] = cover
                with self.assertRaises(ValueError):
                    sync.generate(self.config, projects, self.root)
                self.assertEqual((self.root / 'README.md').read_text(), self.readme)
                self.assertFalse((self.root / 'PROJECTS.md').exists())
                self.assertFalse((self.root / 'assets/projects').exists())

    def test_generation_is_stable_and_removes_obsolete_cards(self):
        items = sync.collect_projects(self.config, [repo('priority')], self.root)
        sync.generate(self.config, items, self.root)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        (self.root / 'assets/projects/obsolete.svg').write_text('old')
        sync.generate(self.config, items, self.root)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_missing_markers_or_empty_result_preserves_previous_output(self):
        with self.assertRaises(ValueError): sync.generate(self.config, [], self.root)
        self.assertEqual((self.root / 'README.md').read_text(), self.readme)
        (self.root / 'README.md').write_text('missing markers')
        with self.assertRaises(ValueError):
            sync.generate(self.config, sync.collect_projects(self.config, [repo('priority')], self.root), self.root)
        self.assertFalse((self.root / 'assets/projects').exists())

    def test_paginates_before_returning_or_propagates_api_failure(self):
        from io import BytesIO
        calls = []
        def respond(request, timeout):
            calls.append(request.full_url)
            return BytesIO(json.dumps([repo(str(i)) for i in range(100)] if len(calls) == 1 else [repo('last')]).encode())
        with patch.object(sync, 'urlopen', side_effect=respond):
            items = sync.fetch_repositories('owner')
        self.assertEqual(len(items), 101)
        self.assertIn('page=2', calls[-1])
        with patch.object(sync, 'urlopen', side_effect=OSError('network failure')):
            with self.assertRaises(OSError): sync.fetch_repositories('owner')


if __name__ == '__main__':
    unittest.main()
