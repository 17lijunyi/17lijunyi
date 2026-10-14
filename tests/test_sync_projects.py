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

    def skill(self, name):
        folder = self.root / 'skills' / name / 'agents'
        folder.mkdir(parents=True)
        (folder.parent / 'SKILL.md').write_text('not executed')
        (folder / 'openai.yaml').write_text(f'interface:\n  display_name: "{name}"\n  short_description: "Skill description"\n')

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
        projects = sync.collect_projects(self.config, [repo('priority'), repo('OvO')] + [repo(f'other-{i}') for i in range(4)], self.root)
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
        self.assertIn('[查看全部项目 →](./PROJECTS.md)', readme)
        self.assertIn('[下载 OvO →]', readme)
        self.assertIn('OvO 应用免费；第三方 API 按服务商规则计费。', readme)
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

    def test_repository_skill_uses_canonical_cover_after_products(self):
        self.skill('example')
        self.config.update(show_all=True, group_by_category=True, compact_cards=True)
        self.config['featured'] = ['repo:chaichai', 'skill:example', 'repo:product']
        cover = 'https://raw.githubusercontent.com/owner/chaichai/main/docs/assets/cover.png'
        self.config['overrides'] = {
            'repo:product': {'category': 'product'},
            'repo:chaichai': {'category': 'skill', 'cover_url': cover},
        }
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            projects = sync.collect_projects(self.config, [repo('chaichai'), repo('product'), repo('plain')], self.root)
        self.assertEqual([item['id'] for item in projects],
                         ['repo:product', 'repo:chaichai', 'skill:example', 'repo:plain'])
        chaichai = projects[1]
        self.assertEqual(chaichai['category'], 'skill')
        self.assertEqual(chaichai['kind'], 'repo')
        self.assertIn('Skill', sync.svg_card(chaichai))
        with patch.object(sync, 'urlopen') as network:
            sync.generate(self.config, projects, self.root)
            network.assert_not_called()
        for filename in ('README.md', 'PROJECTS.md'):
            markup = (self.root / filename).read_text()
            self.assertIn(f'<a href="https://github.com/owner/chaichai"><picture><img width="49%" src="{cover}?v=', markup)
            self.assertEqual(markup.count('<img width="49%"'), 4)
            self.assertLess(markup.index('href="https://github.com/owner/product"'),
                            markup.index('href="https://github.com/owner/chaichai"'))
        readme = (self.root / 'README.md').read_text()
        self.assertTrue(readme.startswith('Personal website\n'))
        self.assertTrue(readme.endswith('\nArticles remain here\n'))
        before = sync.remote_cover_image(cover, chaichai)
        chaichai['updated'] = '2026-10-14T00:00:00Z'
        self.assertNotEqual(before, sync.remote_cover_image(cover, chaichai))

    def test_remote_cover_must_belong_to_its_repository_and_invalid_input_preserves_output(self):
        projects = sync.collect_projects(self.config, [repo('priority')], self.root)
        invalid = [None, 123, 'data:image/png;base64,abc',
                   'http://raw.githubusercontent.com/owner/priority/main/docs/assets/cover.png',
                   'https://raw.githubusercontent.com.evil.test/owner/priority/main/docs/assets/cover.png',
                   'https://raw.githubusercontent.com/other/priority/main/docs/assets/cover.png',
                   'https://raw.githubusercontent.com/owner/elsewhere/main/docs/assets/cover.png',
                   'https://raw.githubusercontent.com/owner/priority/main/../cover.png',
                   'https://raw.githubusercontent.com/owner/priority/main/docs/%2e%2e/cover.png',
                   'https://raw.githubusercontent.com/owner/priority/main/docs//cover.png',
                   'https://raw.githubusercontent.com/owner/priority/main/docs/assets/cover.svg',
                   'https://raw.githubusercontent.com/owner/priority/main/docs/assets/cover.png?token=abc']
        for cover in invalid:
            with self.subTest(cover=cover):
                projects[0]['cover_url'] = cover
                with self.assertRaises(ValueError):
                    sync.generate(self.config, projects, self.root)
                self.assertEqual((self.root / 'README.md').read_text(), self.readme)
                self.assertFalse((self.root / 'PROJECTS.md').exists())
        projects[0].update(cover_url='https://raw.githubusercontent.com/owner/priority/main/docs/assets/cover.png',
                           cover='assets/project-covers/priority.png')
        with self.assertRaisesRegex(ValueError, 'one cover source'):
            sync.generate(self.config, projects, self.root)
        self.assertEqual((self.root / 'README.md').read_text(), self.readme)

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

    def test_category_grouping_preserves_featured_and_recent_order_within_groups(self):
        self.skill('featured-skill')
        self.skill('other-skill')
        self.config['group_by_category'] = True
        self.config['featured'] = ['repo:featured-repository', 'skill:featured-skill', 'repo:featured-product']
        self.config['overrides'] = {
            'repo:featured-product': {'category': 'product'},
            'repo:recent-product': {'category': 'product'},
            'skill:featured-skill': {'category': 'product'},
        }
        repositories = [repo('featured-repository'), repo('featured-product'), repo('recent-product'),
                        repo('old-repository'), repo('recent-repository')]
        repositories[2]['updated_at'] = repositories[4]['updated_at'] = '2026-10-10T00:00:00Z'
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            projects = sync.collect_projects(self.config, repositories, self.root)
            self.assertEqual([project['id'] for project in projects], [
                'repo:featured-product', 'repo:recent-product', 'skill:featured-skill', 'skill:other-skill',
                'repo:featured-repository', 'repo:recent-repository', 'repo:old-repository',
            ])
            self.assertEqual([project['category'] for project in projects],
                             ['product', 'product', 'skill', 'skill', 'repository', 'repository', 'repository'])
            self.config['group_by_category'] = False
            legacy = sync.collect_projects(self.config, repositories, self.root)
        self.assertEqual([project['id'] for project in legacy[:3]], self.config['featured'])

    def test_all_eleven_projects_use_grouped_covers_on_home_and_catalogue(self):
        self.config.update(show_all=True, group_by_category=True)
        self.cover()
        repositories = [repo(f'project-{i}') for i in range(8)]
        for index in range(3):
            self.skill(f'skill-{index}')
            self.config['overrides'][f'skill:skill-{index}'] = {'cover': 'assets/project-covers/priority.png'}
        for index in range(8):
            self.config['overrides'][f'repo:project-{index}'] = {
                'category': 'product' if index < 5 else 'repository',
                'cover': 'assets/project-covers/priority.png',
            }
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            projects = sync.collect_projects(self.config, repositories, self.root)
        sync.generate(self.config, projects, self.root)
        for filename in ('README.md', 'PROJECTS.md'):
            markup = (self.root / filename).read_text()
            self.assertEqual(markup.count('<img width="49%"'), 11)
            self.assertLess(markup.index('### 产品'), markup.index('### Skills'))
            self.assertLess(markup.index('### Skills'), markup.index('### 其他仓库'))
            groups = re.split(r'### (?:产品|Skills|其他仓库)\n\n', markup)[1:]
            self.assertEqual([group.count('<picture>') for group in groups], [5, 3, 3])
            self.assertEqual(markup.count(' · Product'), 5)
            self.assertEqual(markup.count(' · Skills'), 3)
            self.assertEqual(markup.count(' · Repository'), 3)
            rows = re.findall(r'<p>\n(.*?)\n</p>', markup, re.S)
            self.assertEqual([row.count('<img width="49%"') for row in rows], [2, 2, 1, 2, 1, 2, 1])
            for project in projects:
                self.assertIn(f'<a href="{project["url"]}"><picture>', markup)
                self.assertIn(f'alt="{project["title"]}：{project["description"]}"', markup)
            self.assertNotIn('<h2>', markup)
            self.assertNotIn('<p>A project</p>', markup)
        readme = (self.root / 'README.md').read_text()
        self.assertTrue(readme.startswith('Personal website\n'))
        self.assertTrue(readme.endswith('\nArticles remain here\n'))

    def test_show_all_has_no_twelve_card_cap_and_keeps_every_fallback_asset(self):
        self.config.update(show_all=True, group_by_category=True, limit=99)
        sync.validate_config(self.config)
        projects = sync.collect_projects(self.config, [repo(f'project-{i}') for i in range(16)], self.root)
        sync.generate(self.config, projects, self.root)
        self.assertEqual((self.root / 'README.md').read_text().count('<picture>'), 16)
        self.assertEqual((self.root / 'PROJECTS.md').read_text().count('<picture>'), 16)
        self.assertEqual(len(list((self.root / 'assets/projects').glob('*.svg'))), 32)
        (self.root / 'assets/projects/obsolete.svg').write_text('old')
        sync.generate(self.config, projects, self.root)
        self.assertFalse((self.root / 'assets/projects/obsolete.svg').exists())
        self.assertEqual(len(list((self.root / 'assets/projects').glob('*.svg'))), 32)

    def test_compact_eleven_card_wall_crosses_category_boundaries_without_blank_cells(self):
        self.config.update(show_all=True, group_by_category=True, compact_cards=True)
        cover = self.cover('priority-window.png')
        original = cover.read_bytes()
        repositories = [repo(f'product-{i}') for i in range(5)] + [repo('OvO'), repo('knowledge'), repo('daily-news')]
        for index in range(3):
            self.skill(f'skill-{index}')
            self.config['overrides'][f'skill:skill-{index}'] = {'cover': 'assets/project-covers/priority-window.png'}
        for product in repositories[:6]:
            self.config['overrides'][f'repo:{product["name"]}'] = {
                'category': 'product', 'cover': 'assets/project-covers/priority-window.png',
            }
        self.config['overrides']['repo:knowledge'] = {
            'category': 'document', 'cover': 'assets/project-covers/priority-window.png',
        }
        self.config['overrides']['repo:daily-news'] = {'cover': 'assets/project-covers/priority-window.png'}
        # Feature the last category first to verify category order still wins.
        self.config['featured'] = ['repo:daily-news', 'repo:product-0', 'skill:skill-0']
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            projects = sync.collect_projects(self.config, repositories, self.root)
        self.assertEqual([project['category'] for project in projects],
                         ['product'] * 6 + ['skill'] * 3 + ['document', 'repository'])
        sync.generate(self.config, projects, self.root)
        for filename in ('README.md', 'PROJECTS.md'):
            markup = (self.root / filename).read_text()
            rows = re.findall(r'<p>\n(.*?)\n</p>', markup, re.S)
            self.assertEqual([row.count('<img width="49%"') for row in rows], [2, 2, 2, 2, 2, 1])
            image_targets = [re.findall(r'<a href="([^"]+)"><picture>', row) for row in rows]
            self.assertEqual([url for pair in image_targets for url in pair], [project['url'] for project in projects])
            self.assertEqual(image_targets[4], [projects[8]['url'], projects[9]['url']])
            self.assertEqual(image_targets[5], [projects[10]['url']])
            self.assertNotIn('### ', markup)
            self.assertNotIn('<sub>', markup)
            self.assertNotIn('<br>', markup)
            self.assertNotIn('<table', markup)
            self.assertNotIn('[查看全部项目 →]', markup)
            self.assertNotIn('[下载 OvO →]', markup)
            self.assertNotIn('OvO 应用免费；第三方 API 按服务商规则计费。', markup)
            digest = hashlib.sha256(original).hexdigest()[:12]
            self.assertEqual(markup.count(f'priority-window.png?v={digest}'), 11)
            for project in projects:
                self.assertIn(f'alt="{project["title"]}：{project["description"]}"', markup)
        self.assertEqual(cover.read_bytes(), original)

    def test_document_category_sorts_after_skills_and_before_other_repositories(self):
        self.config.update(show_all=True, group_by_category=True)
        self.skill('example')
        self.config['featured'] = ['repo:other', 'repo:older-document']
        self.config['overrides'] = {
            'repo:product': {'category': 'product'},
            'repo:older-document': {'category': 'document'},
            'repo:newer-document': {'category': 'document'},
        }
        repositories = [repo('product'), repo('older-document'), repo('newer-document'), repo('other')]
        repositories[2]['updated_at'] = '2026-10-10T00:00:00Z'
        with patch.object(sync.subprocess, 'check_output', return_value='2026-09-20T00:00:00+00:00\n'):
            projects = sync.collect_projects(self.config, repositories, self.root)
        self.assertEqual([project['id'] for project in projects],
                         ['repo:product', 'skill:example', 'repo:older-document', 'repo:newer-document', 'repo:other'])
        sync.generate(self.config, projects, self.root)
        for filename in ('README.md', 'PROJECTS.md'):
            markup = (self.root / filename).read_text()
            self.assertLess(markup.index('### Skills'), markup.index('### 文档'))
            self.assertLess(markup.index('### 文档'), markup.index('### 其他仓库'))
            self.assertEqual(markup.count(' · Document'), 2)

    def test_compact_new_repository_without_cover_keeps_svg_fallback_and_link(self):
        self.config.update(show_all=True, group_by_category=True, compact_cards=True)
        self.cover('priority-window.png')
        self.config['overrides']['repo:priority'] = {
            'category': 'product', 'cover': 'assets/project-covers/priority-window.png',
        }
        projects = sync.collect_projects(self.config, [repo('priority'), repo('new-repository')], self.root)
        sync.generate(self.config, projects, self.root)
        for filename in ('README.md', 'PROJECTS.md'):
            markup = (self.root / filename).read_text()
            rows = re.findall(r'<p>\n(.*?)\n</p>', markup, re.S)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].count('<img width="49%"'), 2)
            self.assertIn('href="https://github.com/owner/new-repository"><picture>', markup)
            self.assertIn('<source media="(prefers-color-scheme: dark)"', markup)
            self.assertNotIn('### ', markup)
        self.assertEqual(len(list((self.root / 'assets/projects').glob('*.svg'))), 2)
        (self.root / 'assets/projects/obsolete.svg').write_text('old')
        sync.generate(self.config, projects, self.root)
        self.assertFalse((self.root / 'assets/projects/obsolete.svg').exists())
        self.assertEqual(len(list((self.root / 'assets/projects').glob('*.svg'))), 2)

    def test_new_repository_without_a_cover_stays_visible_in_repository_group(self):
        self.config.update(show_all=True, group_by_category=True)
        self.cover()
        self.config['overrides']['repo:priority'] = {'category': 'product', 'cover': 'assets/project-covers/priority.png'}
        projects = sync.collect_projects(self.config, [repo('priority'), repo('new-repository')], self.root)
        sync.generate(self.config, projects, self.root)
        for filename in ('README.md', 'PROJECTS.md'):
            markup = (self.root / filename).read_text()
            repositories = markup.split('### 其他仓库\n\n')[1]
            self.assertIn('href="https://github.com/owner/new-repository"><picture>', repositories)
            self.assertIn(' · Repository', repositories)
            self.assertIn('<source media="(prefers-color-scheme: dark)"', repositories)
        self.assertEqual(len(list((self.root / 'assets/projects').glob('*.svg'))), 2)

    def test_invalid_category_and_mode_flags_fail_without_changing_previous_output(self):
        self.config['overrides']['repo:priority'] = {'category': 'unknown'}
        with self.assertRaisesRegex(ValueError, 'Invalid repository category'):
            sync.collect_projects(self.config, [repo('priority')], self.root)
        self.config['overrides'] = {}
        projects = sync.collect_projects(self.config, [repo('priority')], self.root)
        for flag in ('show_all', 'group_by_category', 'compact_cards'):
            with self.subTest(flag=flag):
                config = dict(self.config, **{flag: 'true'})
                with self.assertRaisesRegex(ValueError, 'must be a boolean'):
                    sync.generate(config, projects, self.root)
        projects[0]['category'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Invalid project category'):
            sync.generate(dict(self.config, group_by_category=True), projects, self.root)
        self.assertEqual((self.root / 'README.md').read_text(), self.readme)
        self.assertFalse((self.root / 'PROJECTS.md').exists())

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
