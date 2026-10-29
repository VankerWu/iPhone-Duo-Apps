#!/usr/bin/env python3
"""Refresh public App Store facts. Never change compatibility verdicts.

Data sources:
- Apple's public Marketing Tools chart RSS JSON (CN/US Top 50 Free)
- Apple's public iTunes Search/Lookup JSON API

No scraping of third-party Duo compatibility sites. Runs on GitHub Actions.
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from store_categories import apply as apply_store_category

DATA = Path(__file__).resolve().parents[1] / 'docs' / 'data' / 'apps.json'
UA = 'iPhone-Duo-App/0.2 (public App Store directory; rate-limited metadata lookups)'
CHART_HOST = 'https://rss.marketingtools.apple.com'
SEARCH_HOST = 'https://itunes.apple.com'
MAX_NEW_PER_REGION = 50


def get_json(url, retries=2):
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(request, timeout=25) as res:
                if res.status != 200:
                    raise ValueError(f'Unexpected HTTP {res.status}')
                return json.load(res)
        except (urllib.error.URLError, ValueError, json.JSONDecodeError, TimeoutError, OSError) as error:
            if attempt == retries:
                print(f'WARNING: fetch failed: {url}: {error}', file=sys.stderr)
                return None
            time.sleep(2 * (attempt + 1))


def norm(text):
    text = unicodedata.normalize('NFKC', str(text or '')).casefold()
    return re.sub(r'[\s.,!()\[\]{}\-–—_:·\u00b7]+', '', text)


def record_from_chart(item, region):
    app_id = str(item.get('id') or '')
    if not app_id.isdigit():
        return None
    name = str(item.get('name') or '').strip()
    if not name:
        return None
    return {
        'id': f'chart-{app_id}', 'name': name, 'english': '', 'category': '热门应用',
        'region': '中国大陆' if region == 'cn' else '美国',
        'status': 'unverified',
        'note': 'App Store 热门榜单收录；不代表已适配 iPhone Duo。',
        'sourceLabel': '', 'sourceUrl': '', 'sourceDate': '', 'verifiedDate': '',
        'searchTerm': name, 'developer': item.get('artistName') or '',
        'version': '', 'releaseDate': '',
        'appStoreUrl': item.get('url') or '', 'artwork': item.get('artworkUrl100') or '',
        'itunesId': int(app_id), 'storefront':region, 'chartRegions': [region]
    }


def match_search(name, results):
    """Return one unambiguous software listing with the same title/root title.

    The App Store frequently appends '- description' or ': description' to
    official titles. Never match by arbitrary substring or best-ranked result.
    """
    target = norm(name)
    if len(target) < 2:
        return None
    hits = []
    for item in results:
        title = str(item.get('trackName') or '').strip()
        if not title or item.get('kind') != 'software':
            continue
        url = str(item.get('trackViewUrl') or '')
        if not url.startswith('https://apps.apple.com/'):
            continue
        if norm(title) == target or any(norm(part) == target for part in
                re.split(r'\s+[-–—:]\s*|\s*[:：]\s*',title,maxsplit=1)[:1]):
            hits.append(item)
    # Multiple matching listings are ambiguous; require a human-verified ID.
    return hits[0] if len(hits) == 1 else None

def apply_metadata(app, track, country='cn'):
    """App Store fields only — DO NOT touch status, note, sourceUrl or sourceDate."""
    if track.get('kind') not in (None, 'software') and track.get('wrapperType') != 'software':
        return
    apply_store_category(app, track, country)
    if str(track.get('currentVersionReleaseDate', '')) < str(app.get('releaseDate', '')):
        return  # Do not downgrade newer page metadata with an older API response.
    app['itunesId'] = track.get('trackId') or app.get('itunesId')
    for field, key in [('developer', 'artistName'), ('version', 'version'),
                       ('releaseDate', 'currentVersionReleaseDate'),
                       ('appStoreUrl', 'trackViewUrl'), ('artwork', 'artworkUrl100')]:
        value = track.get(key)
        if value and isinstance(value, str):
            if field in {'artwork', 'appStoreUrl'} and value.startswith('http://'):
                value = 'https://' + value[7:]
            app[field] = value


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--no-charts', action='store_true', help='Only update known apps')
    argparser.add_argument('--dry-run', action='store_true', help='Read source file but do not contact the network/write')
    argparser.add_argument('--country', choices=('cn', 'us'), help='Limit all Apple requests to one storefront')
    args = argparser.parse_args()
    countries = (args.country,) if args.country else ('cn', 'us')
    catalog = json.loads(DATA.read_text(encoding='utf-8'))
    apps = catalog['apps']
    original = len(apps)
    if args.dry_run:
        print(f'Dry run: {len(apps)} entries; data schema OK')
        return

    by_id = {str(x['itunesId']): x for x in apps if x.get('itunesId')}
    found_chart = 0
    if not args.no_charts:
        for country in countries:
            url = f'{CHART_HOST}/api/v2/{country}/apps/top-free/50/apps.json'
            data = get_json(url)
            results = (data or {}).get('feed', {}).get('results', [])
            print(f'{country.upper()} chart: {len(results)} returned')
            for item in results[:MAX_NEW_PER_REGION]:
                candidate = record_from_chart(item,country)
                if candidate is None:
                    continue
                key = str(candidate['itunesId'])
                if key in by_id:
                    old = by_id[key]
                    old.setdefault('chartRegions', [])
                    if country not in old['chartRegions']:
                        old['chartRegions'].append(country)
                    continue
                # Match an existing editorially curated entry conservatively.
                peers = [x for x in apps if norm(x['name']) == norm(candidate['name'])
                         or (x.get('english') and norm(x['english']) == norm(candidate['name']))]
                if len(peers) == 1 and not peers[0].get('itunesId'):
                    peers[0]['itunesId'] = candidate['itunesId']
                    by_id[key] = peers[0]
                    peers[0].setdefault('chartRegions', []).append(country)
                    if not peers[0].get('appStoreUrl'):
                        peers[0]['appStoreUrl'] = candidate['appStoreUrl']
                    if not peers[0].get('artwork'):
                        peers[0]['artwork'] = candidate['artwork']
                else:
                    apps.append(candidate)
                    by_id[key] = candidate
                    found_chart += 1
            time.sleep(1)

    # IDs come from public chart feeds or previously verified lookups.
    lookup_success_count = 0
    resolved_tracks_count = 0
    for country in countries:
        target = [x for x in apps if x.get('itunesId') and
                  (args.country or x.get('storefront') or ('cn' if x.get('region') == '中国大陆' else 'us')) == country]
        # Keep API requests manageable; grouped ID-based lookups.
        for start in range(0,len(target),35):
            group = target[start:start+35]
            ids = ','.join(str(x['itunesId']) for x in group)
            url = f'{SEARCH_HOST}/lookup?' + urllib.parse.urlencode({'id': ids,'country': country,'entity':'software'})
            info = get_json(url)
            if isinstance(info, dict) and isinstance(info.get('results'), list):
                lookup_success_count += 1
            fetched = {str(t.get('trackId')): t for t in (info or {}).get('results', [])}
            for entry in group:
                meta = fetched.get(str(entry['itunesId']))
                if meta:
                    resolved_tracks_count += 1
                    apply_metadata(entry,meta,country)
            time.sleep(1.2)

    # Resolve App names not yet attached to an iTunes ID.
    # Exact normalized title match only, for a conservative policy.
    missing = [a for a in apps if not a.get('itunesId')]
    for idx,app in enumerate(missing):
        country = args.country or ('cn' if app.get('region') == '中国大陆' else 'us')
        candidates = [app.get('name'), app.get('english'), app.get('searchTerm')]
        candidates = [x for x in dict.fromkeys(candidates) if x]
        for term in candidates[:2]:
            url = f'{SEARCH_HOST}/search?' + urllib.parse.urlencode(
                {'term': term, 'country': country, 'media':'software', 'entity':'software','limit':12})
            info = get_json(url)
            if isinstance(info, dict) and isinstance(info.get('results'), list):
                lookup_success_count += 1
            hit = match_search(term,(info or {}).get('results',[])) if info else None
            if hit:
                resolved_tracks_count += 1
                apply_metadata(app,hit,country)
                break
            time.sleep(1.15)
        if idx and idx % 10 == 0:
            print(f'Name lookups: {idx}/{len(missing)}')

    # Do not claim a fresh successful sync if Apple's lookup API did not respond.
    if lookup_success_count == 0:
        print('WARNING: Apple lookup API returned no usable responses. Existing catalog and sync timestamp left unchanged.')
        return
    print(f'Apple lookup requests succeeded: {lookup_success_count}; matched listings: {resolved_tracks_count}')
    # This timestamp means at least one metadata request succeeded, not every app was matched.
    catalog['lastMetadataSync'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    DATA.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'OK: {len(apps)} catalog entries ({found_chart} newly observed chart apps; original {original}).')
    linked = sum(bool(a.get('itunesId') and a.get('appStoreUrl')) for a in apps)
    icons = sum(bool(a.get('artwork')) for a in apps)
    print(f'Official App Store links: {linked}/{len(apps)}; official artwork: {icons}/{len(apps)}')
    print('Compatibility statuses preserved by policy.')

if __name__ == '__main__':
    main()
