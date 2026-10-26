#!/usr/bin/env python3
"""Add one owner-approved GitHub Issue as an unverified App Store catalog lead.

Invoked by Actions with GITHUB_EVENT_PATH. Only the separate workflow is
responsible for authorizing events. This file never promotes verified status.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'docs/data/apps.json'
MAX_NAME = 100


def normalize(value: str) -> str:
    s = unicodedata.normalize('NFKC', value or '').casefold()
    return re.sub(r'[\s,，.。!！:：·\-–—_()（）\[\]【】]+', '', s)


def sections(body: str) -> dict[str, str]:
    """Support GitHub issue forms (###) and existing prefilled issues (##)."""
    chunks = re.split(r'(?m)^#{2,3}\s+([^\n]+)\s*\n', body or '')
    return {chunks[i].strip(): chunks[i + 1].strip() for i in range(1, len(chunks) - 1, 2)}


def get_field(fields: dict[str, str], *names: str) -> str:
    for name in names:
        value = fields.get(name, '').strip()
        if value and value.lower() not in ('_no response_', 'none', '无', 'n/a'):
            return value
    return ''


def apple_id_from_url(raw: str) -> tuple[int, str] | None:
    """Official store product URLs only, not Apple search or arbitrary sites."""
    match = re.search(r'https://apps\.apple\.com/[^\s<>\])]+', raw or '', re.I)
    if not match:
        return None
    try:
        url = urllib.parse.urlsplit(match.group().rstrip('.,。，'))
    except ValueError:
        return None
    if url.scheme != 'https' or (url.hostname or '').lower() != 'apps.apple.com':
        return None
    match_id = re.search(r'/id(\d{5,15})(?:/|$)', url.path)
    if not match_id:
        return None
    country = url.path.strip('/').split('/')[0].lower()
    return int(match_id.group(1)), ('cn' if country in ('cn','hk','tw','mo') else 'us')


def request_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={'Accept':'application/json', 'User-Agent':'iPhone-Duo-Apps-Issues-Bot/1.0'})
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.load(response)
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        print('Apple lookup temporarily unavailable:', error, file=sys.stderr)
        return None


def lookup_track(app_id: int, country: str) -> dict | None:
    query = urllib.parse.urlencode({'id':app_id,'country':country,'entity':'software'})
    data = request_json('https://itunes.apple.com/lookup?' + query)
    for item in (data or {}).get('results', []):
        if item.get('trackId') == app_id and item.get('kind') in (None,'software'):
            return item
    return None


def search_unique(name: str, country: str) -> tuple[int, dict] | None:
    """No guessing: require exactly one exact/root name match."""
    query = urllib.parse.urlencode({'term':name,'country':country,'entity':'software','limit':45})
    data = request_json('https://itunes.apple.com/search?' + query)
    matches: dict[int,dict] = {}
    for item in (data or {}).get('results', []):
        full = str(item.get('trackName') or '').strip()
        if item.get('kind') not in (None,'software') or not full:
            continue
        root = re.split(r'\s*[-–—:：]\s*', full, maxsplit=1)[0]
        if normalize(full) == normalize(name) or normalize(root) == normalize(name):
            if isinstance(item.get('trackId'), int):
                matches[item['trackId']] = item
    if len(matches) == 1:
        return next(iter(matches.items()))
    return None


def apple_artwork(track: dict | None) -> str:
    url = str((track or {}).get('artworkUrl512') or (track or {}).get('artworkUrl100') or '')
    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or '').lower()
        return url if parsed.scheme == 'https' and (host == 'mzstatic.com' or host.endswith('.mzstatic.com')) else ''
    except ValueError:
        return ''


def parse_issue(event: dict, *, resolver=None) -> dict:
    issue = event.get('issue', {})
    fields = sections(issue.get('body') or '')
    name = get_field(fields, 'App 名称', '应用名称', 'App 名称及 App Store 链接')
    if not name:
        title = re.sub(r'^\s*\[(?:收录|反馈|实测)\]\s*', '', issue.get('title','')).strip()
        name = title.split(' - ')[0].strip()
    if not name or len(name) > MAX_NAME or '\n' in name or name in ('App 名称','请填写'):
        raise ValueError('请在表单中填写准确的 App 名称（不超过100字）')
    store_text = get_field(fields, 'App Store 链接', 'App 名称及 App Store 链接')
    store = apple_id_from_url(store_text)
    region_text = get_field(fields, '主要地区', '地区')
    country = 'us' if region_text in ('美国','US','全球') else 'cn'
    track = None
    if store:
        app_id, country = store
        if resolver is not None:
            track = resolver(app_id, country)
        else:
            track = lookup_track(app_id, country)
    else:
        found = search_unique(name, country) if resolver is None else resolver(None, country, name)
        if not found:
            raise ValueError('没有提供官方 App Store 商品页，且无法唯一匹配应用。请补充正确的 apps.apple.com 商品链接后重试。')
        app_id, track = found
    category = get_field(fields,'应用分类','分类')
    allowed = {'影音娱乐','效率办公','社交通讯','摄影创作','购物生活','出行导航','阅读','体育','健康运动','金融理财','其他应用'}
    if category not in allowed:
        category = '其他应用'
    return {
        'name':name,
        'itunesId':app_id,
        'storefront':country,
        'region':'中国大陆' if country == 'cn' else '全球',
        'category':category,
        'track':track,
    }


def update_catalog(catalog: dict, record: dict, issue: dict, repo: str, today: str) -> str:
    apps = catalog.get('apps')
    if not isinstance(apps, list):
        raise ValueError('apps.json 缺少 apps 数组')
    store_id = record['itunesId']
    issue_url = f"https://github.com/{repo}/issues/{int(issue['number'])}"
    for old in apps:
        if int(old.get('itunesId') or 0) == store_id or normalize(old.get('name','')) == normalize(record['name']):
            reports = old.setdefault('communityIssueReports',[])
            if not isinstance(reports, list):
                reports = old['communityIssueReports'] = []
            if issue_url not in reports:
                reports.append(issue_url)
                # Never override Apple/verified judgments or manually curated notes.
                return 'existing-updated'
            return 'unchanged'
    track = record['track'] or {}
    name = record['name']
    app_id = store_id
    country = record['storefront']
    apps.append({
        'id':f'community-issue-app-{app_id}',
        'name':name,
        'english':str(track.get('trackName') or '')[:130],
        'category':record['category'],
        'region':record['region'],
        'status':'unverified',
        'note':'社区提供了 iPhone Duo 适配线索；尚未完成独立实机核验。',
        'sourceLabel':'社区提交 · GitHub Issues（待核验）',
        'sourceUrl':issue_url,
        'sourceDate':today,
        'verifiedDate':'',
        'searchTerm':name,
        'developer':str(track.get('artistName') or '')[:100],
        'version':str(track.get('version') or '')[:40],
        'releaseDate':str(track.get('currentVersionReleaseDate') or '')[:35],
        'appStoreUrl':f'https://apps.apple.com/{country}/app/id{app_id}',
        'artwork':apple_artwork(track),
        'itunesId':app_id,
        'storefront':country,
        'communityIssueReports':[issue_url],
    })
    return 'added'


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python scripts/ingest_issue.py path/to/event.json', file=sys.stderr)
        return 2
    event = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    issue = event['issue']
    repo = os.environ.get('GITHUB_REPOSITORY','VankerWu/iPhone-Duo-Apps')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('Invalid repository')
    status_file = os.environ.get('GITHUB_OUTPUT')
    def output(key, value):
        if status_file:
            with open(status_file,'a',encoding='utf-8') as output_file:
                output_file.write(f'{key}={value}\n')
    try:
        record = parse_issue(event)
        data = json.loads(CATALOG.read_text(encoding='utf-8'))
        state = update_catalog(data,record,issue,repo,dt.datetime.now(dt.timezone.utc).date().isoformat())
        if state != 'unchanged':
            CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        output('status',state)
        print(f'Catalog issue #{issue["number"]}: {state}; {record["name"]} id{record["itunesId"]}')
        return 0
    except (ValueError, KeyError, TypeError) as error:
        print('Issue requires more information:',error,file=sys.stderr)
        output('status','needs-info')
        output('message','请提供准确的 App 名称和官方 App Store 商品页链接，然后回复 `/收录` 重新提交。')
        # Don't break scheduled site updates due to one incomplete user report.
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
