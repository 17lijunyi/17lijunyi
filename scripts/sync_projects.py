#!/usr/bin/env python3
"""Generate self-hosted project cards using public GitHub metadata and local skills."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- PROJECTS:START -->'
END = '<!-- PROJECTS:END -->'
COLORS = {'Swift': '#f05138', 'Python': '#3572A5', 'HTML': '#e34c26',
          'JavaScript': '#f1e05a', 'TypeScript': '#3178c6', 'CSS': '#663399',
          'Go': '#00ADD8', 'Rust': '#dea584', 'Shell': '#89e051'}


def fetch_repositories(owner):
    repositories = []
    for page in range(1, 101):
        url = f'https://api.github.com/users/{quote(owner, safe="")}/repos?type=owner&per_page=100&page={page}'
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-project-cards',
                   'X-GitHub-Api-Version': '2022-11-28'}
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Expected a repository list')
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
    raise ValueError('Repository pagination exceeded limit; keeping previous catalogue')


def scalar(source, key):
    # Only read display metadata; never execute or interpret skill instructions.
    match = re.search(r'^\s*' + re.escape(key) + r':\s*(.+)$', source, re.M)
    if not match:
        return ''
    value = match.group(1).strip()
    if value.startswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def collect_projects(config, repositories, root=ROOT):
    owner = config['owner']
    projects = []
    for repo in repositories:
        if (repo.get('private') or repo.get('visibility', 'public') != 'public'
                or repo.get('fork') or repo.get('archived')
                or repo['name'] in config['exclude']
                or repo.get('owner', {}).get('login', '').lower() != owner.lower()):
            continue
        projects.append({'id': 'repo:' + repo['name'], 'kind': 'repo',
                         'title': repo['name'], 'description': repo.get('description') or '查看项目介绍、代码与使用说明。',
                         'url': f'https://github.com/{owner}/{quote(repo["name"], safe="")}',
                         'language': repo.get('language'), 'stars': repo['stargazers_count'],
                         'forks': repo['forks_count'], 'updated': repo['updated_at']})
    for skill in sorted((root / 'skills').glob('*/SKILL.md')):
        directory = skill.parent
        metadata = directory / 'agents/openai.yaml'
        if not metadata.is_file():
            continue
        source = metadata.read_text()
        title, description = scalar(source, 'display_name'), scalar(source, 'short_description')
        if not title or not description:
            continue
        relative = directory.relative_to(root).as_posix()
        updated = subprocess.check_output(['git', 'log', '-1', '--format=%cI', '--', relative], cwd=root, text=True).strip()
        projects.append({'id': 'skill:' + directory.name, 'kind': 'skill', 'title': title,
                         'description': description, 'url': f'https://github.com/{owner}/{config["profile_repo"]}/tree/main/{quote(relative)}',
                         'updated': updated})
    for item in projects:
        overrides = config.get('overrides', {}).get(item['id'], {})
        for key in ('title', 'description'):
            if overrides.get(key):
                item[key] = overrides[key]
    featured = {key: rank for rank, key in enumerate(config['featured'])}
    projects.sort(key=lambda p: (p['updated'], p['id']), reverse=True)
    projects.sort(key=lambda p: featured.get(p['id'], len(featured)))
    return projects


def units(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1.2 for c in text)


def wrap(text, width, lines):
    text = ' '.join(text.split())
    result, line = [], ''
    for c in text:
        if units(line + c) > width and line:
            result.append(line.rstrip())
            line = c.lstrip()
        else:
            line += c
    if line:
        result.append(line.rstrip())
    if len(result) > lines:
        result = result[:lines]
        while units(result[-1] + '…') > width:
            result[-1] = result[-1][:-1]
        result[-1] = result[-1].rstrip() + '…'
    return result


def svg_card(project, dark=False):
    bg, border, text, muted, link = ('#0d1117', '#30363d', '#f0f6fc', '#9198a1', '#4493f8') if dark else ('#ffffff', '#d1d9e0', '#1f2328', '#59636e', '#0969da')
    esc = html.escape
    title = wrap(project['title'], 40, 1)[0]
    desc = wrap(project['description'], 56, 3)
    badge = 'Skill' if project['kind'] == 'skill' else 'Public'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="210" viewBox="0 0 620 210" role="img" aria-labelledby="title desc">',
             f'<title id="title">{esc(project["title"])}</title><desc id="desc">{esc(project["description"])}</desc>',
             f'<rect x=".75" y=".75" width="598.5" height="208.5" rx="9" fill="{bg}" stroke="{border}" stroke-width="1.5"/>',
             '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans CJK SC,PingFang SC,Microsoft YaHei,sans-serif">',
             f'<g transform="translate(24 24)" fill="none" stroke="{muted}" stroke-width="1.7"><path d="M3 2h15v20H3a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm-2 15h17M5 17v7l3-2 3 2v-7"/></g>',
             f'<text x="56" y="43" fill="{link}" font-size="22" font-weight="600">{esc(title)}</text>',
             f'<rect x="512" y="23" width="64" height="26" rx="13" fill="none" stroke="{border}"/>',
             f'<text x="544" y="41" text-anchor="middle" fill="{muted}" font-size="15">{badge}</text>']
    for index, line in enumerate(desc):
        parts.append(f'<text x="24" y="{81 + index * 27}" fill="{muted}" font-size="19">{esc(line)}</text>')
    if project['kind'] == 'skill':
        parts += [f'<circle cx="31" cy="177" r="7" fill="#8250df"/>',
                  f'<text x="47" y="183" fill="{muted}" font-size="17">技能目录</text>']
    else:
        lang = project['language']
        if lang:
            parts += [f'<circle cx="31" cy="177" r="7" fill="{COLORS.get(lang, "#8b949e")}"/>',
                      f'<text x="47" y="183" fill="{muted}" font-size="17">{esc(wrap(lang, 19, 1)[0])}</text>']
        for x, kind, value in [(230, 'star', project['stars']), (350, 'fork', project['forks'])]:
            path = '<path d="m10 1 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L1 7.6l6.2-.9Z"/>' if kind == 'star' else '<circle cx="5" cy="3" r="2.5"/><circle cx="15" cy="3" r="2.5"/><circle cx="10" cy="17" r="2.5"/><path d="M5 5.5V8c0 3 10 3 10 0V5.5M10 10v4.5"/>'
            parts += [f'<g transform="translate({x} 166)" fill="none" stroke="{muted}" stroke-width="1.6">{path}</g>',
                      f'<text x="{x + 28}" y="183" fill="{muted}" font-size="17">{int(value)}</text>']
    return '\n'.join(parts + ['</g></svg>']) + '\n'


def replace_section(readme, content):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError('README must have exactly one pair of project markers')
    before, rest = readme.split(START)
    _, after = rest.split(END)
    return before + START + '\n' + content + '\n' + END + after


def generate(config, projects, root=ROOT):
    if not projects:
        raise ValueError('No projects returned; keeping existing cards')
    chosen = projects[:config['limit']]
    files, cards = {}, []
    base = f'https://raw.githubusercontent.com/{config["owner"]}/{config["profile_repo"]}/main/'
    for project in chosen:
        key = hashlib.sha256(project['id'].encode()).hexdigest()[:12]
        images = {}
        for theme in ('light', 'dark'):
            path = f'assets/projects/{key}-{theme}.svg'
            content = svg_card(project, theme == 'dark')
            files[path] = content
            images[theme] = base + path + '?v=' + hashlib.sha256(content.encode()).hexdigest()[:12]
        alt = html.escape(project['title'] + '：' + project['description'], quote=True)
        cards.append(f'  <a href="{html.escape(project["url"], quote=True)}"><picture><source media="(prefers-color-scheme: dark)" srcset="{images["dark"]}"><img width="49%" src="{images["light"]}" alt="{alt}"></picture></a>')
    rows = ['<p>\n' + '\n'.join(cards[i:i + 2]) + '\n</p>' for i in range(0, len(cards), 2)]
    rows += ['[查看全部项目 →](./PROJECTS.md) · [下载 OvO →](https://github.com/17lijunyi/OvO/releases/latest)']
    if any(p['id'] == 'repo:OvO' for p in chosen):
        rows += ['<sub>OvO 应用免费；第三方 API 按服务商规则计费。</sub>']
    files['README.md'] = replace_section((root / 'README.md').read_text(), '\n\n'.join(rows))
    catalogue = ['# 全部项目', '', '重点项目优先，其余按最近更新时间排列。', '',
                 f'[返回主页](https://github.com/{config["owner"]}) · [个人网站](https://{config["owner"]}.github.io/) · [所有公开仓库](https://github.com/{config["owner"]}?tab=repositories)', '']
    for p in projects:
        # HTML escapes keep remote metadata inert in Markdown rendering.
        catalogue += [f'<h2><a href="{html.escape(p["url"], quote=True)}">{html.escape(p["title"])}</a></h2>',
                      '', f'<p>{html.escape(p["description"])}</p>', '']
        if p['kind'] == 'repo':
            stats = f'{p["language"] or "未标注语言"} · Star {p["stars"]} · Fork {p["forks"]}'
        else:
            stats = '技能目录'
        catalogue += [f'<p><sub>{html.escape(stats)}</sub></p>', '']
    files['PROJECTS.md'] = '\n'.join(catalogue)
    # Validate everything in memory before changing any generated file.
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    for path in (root / 'assets/projects').glob('*.svg'):
        if path.relative_to(root).as_posix() not in files:
            path.unlink()
    print(f'Generated {len(chosen)} cards; catalogue contains {len(projects)} projects.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repos-json', type=Path, help='Use a local API fixture instead of a network request')
    args = parser.parse_args()
    config = json.loads((ROOT / 'projects.json').read_text())
    if not isinstance(config['limit'], int) or not 1 <= config['limit'] <= 12:
        raise ValueError('Card limit must be between 1 and 12')
    repos = json.loads(args.repos_json.read_text()) if args.repos_json else fetch_repositories(config['owner'])
    generate(config, collect_projects(config, repos))


if __name__ == '__main__':
    main()
