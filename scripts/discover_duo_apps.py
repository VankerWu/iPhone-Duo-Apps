#!/usr/bin/env python3
"""Find *candidate* iPhone Duo apps using Apple's public metadata.

Only an iPhone Duo mention with support/layout wording, without detected
negative/future wording in the same sentence, qualifies as a candidate. Candidates are NOT automatically verified as
compatible. Published catalog entries are always `unverified` unless human
review has independently confirmed a stronger status.

No dependencies beyond Python 3's standard library. Does not copy code,
compatibility verdicts or datasets from third-party directory sites.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'data' / 'apps.json'
REVIEW = ROOT / 'docs' / 'data' / 'duo-review-queue.json'
APPLE_LOOKUP = 'https://itunes.apple.com/lookup'
CHART_HOST = 'https://rss.marketingtools.apple.com'
USER_AGENT = 'iPhone-Duo-Apps/1.0 (Apple public metadata; conservative evidence review)'
# Only a specific product reference. Do not treat 'duo', 'foldable', 'optimized'
# alone as evidence, and never infer compatibility from a release date.
MENTION = re.compile(r'iphone[\s\-\u2013\u2014]*duo', flags=re.IGNORECASE)
SUPPORT = re.compile(r'support|compatib|optimi[sz]|adapt|layout|split[ -]?screen|支持|适配|兼容|优化|佈局|布局|分屏', re.I)
MAX_CHART = 100
SEARCH_TERMS = ("iPhone Duo", "iPhone-Duo")
NEGATIVE = re.compile(r"not\s+(?:yet\s+)?support|unsupported|coming\s+soon|future\s+(?:update|support)|planned|尚不支持|暂不支持|不支持|尚未|暂未|即将|计划|敬请期待", re.I)
BATCH_SIZE = 30


def get_json(url: str, *, retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'Accept': 'application/json', 'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=18) as response:
                if response.status != 200:
                    raise ValueError(f'HTTP {response.status}')
                value = json.load(response)
                if not isinstance(value, dict):
                    raise ValueError('Unexpected JSON payload')
                return value
        except (urllib.error.URLError, OSError, TimeoutError,
                ValueError, json.JSONDecodeError) as exc:
            if attempt == retries:
                print(f'WARNING: Apple endpoint unavailable: {url[:115]}: {exc}', file=sys.stderr)
                return None
            time.sleep(attempt + 1)
    return None


def safe_apple_url(value: str) -> str:
    """Do not embed arbitrary URLs from remote JSON into the public catalog."""
    try:
        u = urllib.parse.urlsplit(str(value or ''))
        if u.scheme != 'https' or u.username or u.password or u.port:
            return ''
        if u.hostname not in ('apps.apple.com', 'itunes.apple.com'):
            return ''
        return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, u.query, ''))
    except ValueError:
        return ''


def safe_artwork(value: str) -> str:
    try:
        u = urllib.parse.urlsplit(str(value or ''))
        if u.scheme != 'https' or u.username or u.password or u.port:
            return ''
        hostname = u.hostname or ''
        if not (hostname == 'mzstatic.com' or hostname.endswith('.mzstatic.com')):
            return ''
        return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, u.query, ''))
    except ValueError:
        return ''


def excerpt(notes: str, limit: int = 380) -> str:
    """Return an evidence excerpt surrounding the actual mention."""
    notes = re.sub(r'\s+', ' ', str(notes or '')).strip()
    match = MENTION.search(notes)
    if not match:
        return ''
    start = max(0, match.start() - 110)
    end = min(len(notes), match.end() + limit - 110)
    prefix = '…' if start else ''
    suffix = '…' if end < len(notes) else ''
    return prefix + notes[start:end] + suffix


def initial_review_queue() -> dict:
    return {'schemaVersion': 1,
            'description': '机器发现的 App Store 更新说明线索。须人工审查，绝不自动标记已适配。',
            'candidates': []}


def candidate_record(track: dict, region: str, checked_at: str) -> dict | None:
    identifier = track.get('trackId')
    if not (isinstance(identifier, int) and identifier > 0):
        return None
    # Apple sometimes omits kind but retains wrapperType for app responses.
    if track.get('kind') not in (None, 'software'):
        return None
    if track.get('wrapperType') not in (None, 'software'):
        return None
    notes = str(track.get('releaseNotes') or '')
    snippet = excerpt(notes)
    if not snippet:
        return None
    # Keep negative/future statements out of the public directory.
    sentences = re.split(r'[.!?。！？\n]+', notes)
    relevant = [line for line in sentences if MENTION.search(line)]
    if not any(SUPPORT.search(line) and not NEGATIVE.search(line) for line in relevant):
        return None
    app_url = safe_apple_url(track.get('trackViewUrl') or '')
    if not app_url:
        return None
    name = str(track.get('trackName') or '').strip()
    if not name:
        return None
    return {
        'itunesId': identifier,
        'name': name[:160],
        'storefront': region,
        'version': str(track.get('version') or '')[:60],
        'releaseDate': str(track.get('currentVersionReleaseDate') or '')[:30],
        'evidenceType': 'app_store_release_notes_mention',
        'evidenceExcerpt': snippet,
        'appStoreUrl': app_url,
        'artwork': safe_artwork(track.get('artworkUrl512') or track.get('artworkUrl100') or ''),
        'developer': str(track.get('artistName') or '')[:200],
        'firstSeen': checked_at,
        'lastSeen': checked_at,
        'reviewStatus': 'pending',
    }


def new_catalog_entry(candidate: dict) -> dict:
    region = candidate['storefront']
    return {
        'id': 'signal-' + str(candidate['itunesId']),
        'name': candidate['name'], 'english': '', 'category': '新适配线索',
        'region': '中国大陆' if region == 'cn' else '美国',
        'status': 'unverified',
        'note': 'App Store 更新说明提及 iPhone Duo；是否真正适配仍待核验。',
        'sourceLabel': '', 'sourceUrl': '', 'sourceDate': '', 'verifiedDate': '',
        'searchTerm': candidate['name'], 'developer': candidate['developer'],
        'version': candidate['version'], 'releaseDate': candidate['releaseDate'],
        'appStoreUrl': candidate['appStoreUrl'], 'artwork': candidate['artwork'],
        'itunesId': candidate['itunesId'], 'storefront': region,
        'duoDiscovery': {
            'type': candidate['evidenceType'],
            'version': candidate['version'],
            'excerpt': candidate['evidenceExcerpt'],
            'url': candidate['appStoreUrl'],
            'date': candidate['releaseDate'][:10],
        },
    }


def apply_candidate(app: dict, candidate: dict) -> None:
    # NEVER overwrite human reviewed statuses, notes, citations or dates.
    app['duoDiscovery'] = {
        'type': candidate['evidenceType'],
        'version': candidate['version'],
        'excerpt': candidate['evidenceExcerpt'],
        'url': candidate['appStoreUrl'],
        'date': candidate['releaseDate'][:10],
    }
    for field in ('artwork', 'appStoreUrl', 'developer', 'version', 'releaseDate'):
        if candidate.get(field) and not app.get(field):
            app[field] = candidate[field]


def discover(catalog: dict, queue: dict, fetch=get_json,
             *, pause: bool = False, checked_at: str | None = None) -> tuple[int, int, int]:
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    apps = catalog['apps']
    by_id = {int(a['itunesId']): a for a in apps if str(a.get('itunesId') or '').isdigit()}
    previously = {int(c['itunesId']): c for c in queue.get('candidates', []) if str(c.get('itunesId') or '').isdigit()}
    targets: dict[str, set[int]] = {'cn': set(), 'us': set()}

    # Existing catalog entries need ongoing version checks even when they fall
    # off the charts. Region-specific lookups respect catalog storefronts.
    for key, app in by_id.items():
        region = app.get('storefront') or ('cn' if app.get('region') == '中国大陆' else 'us')
        targets[region if region in targets else 'us'].add(key)

    # Continue watching queued candidates even after they leave the charts.
    for key, item in previously.items():
        region = item.get('storefront', 'us')
        targets[region if region in targets else 'us'].add(key)

    responses = 0
    lookup_responses = 0
    chart_returned = 0
    for region in ('cn', 'us'):
        for chart in ('top-free', 'top-paid'):
            url = f'{CHART_HOST}/api/v2/{region}/apps/{chart}/{MAX_CHART}/apps.json'
            data = fetch(url)
            feed = data.get('feed', {}) if isinstance(data, dict) else {}
            entries = feed.get('results') if isinstance(feed, dict) else None
            if isinstance(entries, list):
                responses += 1
                for item in entries[:MAX_CHART]:
                    if isinstance(item, dict) and str(item.get('id') or '').isdigit():
                        targets[region].add(int(item['id']))
                        chart_returned += 1
            if pause:
                time.sleep(.65)
        # Search supplies additional leads outside the charts. Search relevance
        # never qualifies an app: lookup releaseNotes must still pass evidence checks.
        for term in SEARCH_TERMS:
            params = urllib.parse.urlencode({'term': term, 'country': region,
                'media': 'software', 'entity': 'software', 'limit': 200})
            data = fetch('https://itunes.apple.com/search?' + params)
            entries = data.get('results') if isinstance(data, dict) else None
            if isinstance(entries, list):
                responses += 1
                for item in entries[:200]:
                    ident = item.get('trackId') if isinstance(item, dict) else None
                    if isinstance(ident, int) and not isinstance(ident, bool) and ident > 0:
                        targets[region].add(ident)
            if pause:
                time.sleep(.65)

    signals = 0
    inserted = 0
    for region in ('cn', 'us'):
        identifiers = sorted(targets[region])
        for offset in range(0, len(identifiers), BATCH_SIZE):
            batch = identifiers[offset:offset + BATCH_SIZE]
            parameters = urllib.parse.urlencode({
                'id': ','.join(map(str, batch)), 'country': region, 'entity': 'software'})
            data = fetch(APPLE_LOOKUP + '?' + parameters)
            if not isinstance(data, dict) or not isinstance(data.get('results'), list):
                continue
            responses += 1
            lookup_responses += 1
            for track in data['results']:
                if not isinstance(track, dict):
                    continue
                if track.get('trackId') not in batch:
                    continue
                candidate = candidate_record(track, region, checked_at)
                if not candidate:
                    continue
                ident = candidate['itunesId']
                signals += 1
                if ident in previously:
                    original = previously[ident]
                    candidate['firstSeen'] = original.get('firstSeen') or checked_at
                    # Preserve human decisions about items in the review queue.
                    candidate = {**original, **candidate,
                                 'reviewStatus': original.get('reviewStatus', 'pending')}
                previously[ident] = candidate
                if candidate['reviewStatus'] != 'pending':
                    continue
                if ident not in by_id:
                    entry = new_catalog_entry(candidate)
                    apps.append(entry)
                    by_id[ident] = entry
                    inserted += 1
                else:
                    apply_candidate(by_id[ident], candidate)
            if pause:
                time.sleep(.65)

    if lookup_responses == 0:
        raise RuntimeError('No usable Apple lookup responses. No catalog changes were written.')

    catalog['lastDiscoverySync'] = checked_at
    queue['lastChecked'] = checked_at
    queue['candidates'] = sorted(previously.values(),
                                 key=lambda c: (c.get('reviewStatus') != 'pending',
                                                -(int(c['itunesId']))))
    print(f'Discovery checked {sum(map(len, targets.values()))} storefront listings '
          f'({chart_returned} chart entries), found {signals} mentions, '
          f'added {inserted} pending-verification apps; existing confirmed statuses preserved.')
    return inserted, signals, responses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Validate local catalog/queue without network')
    parser.add_argument('--catalog', type=Path, default=DATA)
    parser.add_argument('--queue', type=Path, default=REVIEW)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text('utf-8'))
    if not isinstance(catalog.get('apps'), list):
        raise ValueError('Catalog must have an apps array')
    queue = json.loads(args.queue.read_text('utf-8')) if args.queue.exists() else initial_review_queue()
    if not isinstance(queue.get('candidates'), list):
        raise ValueError('Candidate queue must have a candidates array')
    if args.dry_run:
        print(f'OK: catalog {len(catalog["apps"])} entries; '
              f'candidate queue {len(queue["candidates"])}; no network or writes')
        return
    discover(catalog, queue, pause=True)
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    args.queue.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + '\n', 'utf-8')


if __name__ == '__main__':
    main()
