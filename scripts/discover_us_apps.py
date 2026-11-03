#!/usr/bin/env python3
"""Bounded US storefront discovery; reuse conservative evidence rules.

Pool/cursors/coverage are independent from CN. No name-based deduplication,
no public listing until an explicit version note qualifies, no review promotion.
"""
from __future__ import annotations

import datetime as dt
import time
import urllib.parse
import urllib.request

from discover_duo_apps import (APPLE_LOOKUP, CHART_HOST, MAX_CHART, GENRES,
    GAME_GENRES, GENRES_PER_RUN, GAME_GENRES_PER_RUN, LOOKUPS_PER_RUN, BATCH_SIZE,
    USER_AGENT, MENTION, get_json, category_ids, rotate, candidate_record,
    new_catalog_entry, apply_candidate, page_versions)
from store_categories import positive_id, apply as apply_category
from storefront_data import primary_store, remember_listing, merge_candidate

US_SEARCH_TERMS = ('iPhone Duo', 'iPhone-Duo', 'iPhone Duo support', 'iPhone Duo game')


def get_page(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read(3000000).decode('utf-8')


def discover_us(catalog, queue, fetch=get_json, fetch_page=get_page, *,
                page_limit=30, max_seconds=720, checked_at=None, pause=False,
                clock=time.monotonic):
    started = clock()
    checked_at = checked_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    by_id = {ident: app for app in catalog['apps'] if (ident := positive_id(app.get('itunesId')))}
    previous = {ident: item for item in queue['candidates'] if (ident := positive_id(item.get('itunesId')))}
    pool = {ident for raw in queue.get('discoveryPoolUS', []) if (ident := positive_id(raw))}
    # An existing CN ID is only a lookup target, not proof of US availability.
    pool.update(by_id)
    pool.update(previous)
    coverage = {'time': checked_at, 'poolSize': 0, 'lookupScheduled': 0,
                'lookupAttempted': 0, 'lookupReturned': 0, 'lookupRequestsSucceeded': 0,
                'categoryFeedsAttempted': 0, 'categoryFeedsSucceeded': 0,
                'gameFeedsAttempted': 0, 'gameFeedsSucceeded': 0,
                'sourceRequestsAttempted': 0, 'sourceRequestsFailed': 0,
                'pagesAttempted': 0, 'pagesParsed': 0, 'pagesFailed': 0}
    tracks = {}

    def remaining():
        return clock() - started < max_seconds

    def request(url):
        if not remaining():
            return None
        try:
            return fetch(url)
        except (OSError, ValueError):
            return None

    def source(url):
        coverage['sourceRequestsAttempted'] += 1
        result = request(url)
        if not isinstance(result, dict):
            coverage['sourceRequestsFailed'] += 1
        return result

    for chart in ('top-free', 'top-paid'):
        if not remaining():
            break
        data = source(f'{CHART_HOST}/api/v2/us/apps/{chart}/{MAX_CHART}/apps.json')
        feed = data.get('feed', {}) if isinstance(data, dict) else {}
        entries = feed.get('results', []) if isinstance(feed, dict) else []
        for item in entries[:MAX_CHART] if isinstance(entries, list) else []:
            if isinstance(item, dict) and (ident := positive_id(item.get('id'))):
                pool.add(ident)
    for term in US_SEARCH_TERMS:
        if not remaining():
            break
        params = urllib.parse.urlencode({'term': term, 'country': 'us',
            'media': 'software', 'entity': 'software', 'limit': 200})
        data = source('https://itunes.apple.com/search?' + params)
        entries = data.get('results', []) if isinstance(data, dict) else []
        for item in entries[:200] if isinstance(entries, list) else []:
            if isinstance(item, dict) and (ident := positive_id(item.get('trackId'))):
                pool.add(ident)

    for genres, cursor_key, count, is_game in (
        (GENRES, 'genreCursorUS', GENRES_PER_RUN, False),
        (GAME_GENRES, 'gameGenreCursorUS', GAME_GENRES_PER_RUN, True),
    ):
        selected, _ = rotate(genres, queue.get(cursor_key, 0), count)
        attempted = 0
        for genre in selected:
            if not remaining():
                break
            attempted += 1
            for chart in ('topfreeapplications', 'toppaidapplications'):
                if not remaining():
                    break
                coverage['categoryFeedsAttempted'] += 1
                if is_game:
                    coverage['gameFeedsAttempted'] += 1
                data = source(f'https://itunes.apple.com/us/rss/{chart}/limit=100/genre={genre}/json')
                if isinstance(data, dict) and isinstance(data.get('feed'), dict):
                    coverage['categoryFeedsSucceeded'] += 1
                    if is_game:
                        coverage['gameFeedsSucceeded'] += 1
                    pool.update(category_ids(data))
        _, queue[cursor_key] = rotate(genres, queue.get(cursor_key, 0), attempted)

    selected, _ = rotate(pool, queue.get('lookupCursorUS', 0), LOOKUPS_PER_RUN)
    coverage['poolSize'] = len(pool)
    coverage['lookupScheduled'] = len(selected)
    queue['discoveryPoolUS'] = sorted(pool)
    attempted = 0

    def process(track):
        ident = positive_id(track.get('trackId'))
        if not ident:
            return
        if ident in by_id:
            app = by_id[ident]
            remember_listing(app, track, 'us', checked_at)
            apply_category(app, track, 'us')
            if primary_store(app) == 'us':
                facts = app.get('storeListings', {}).get('us', {})
                if facts.get('releaseDate', '')[:10] >= str(app.get('releaseDate', ''))[:10]:
                    for key in ('version', 'releaseDate', 'developer', 'appStoreUrl', 'artwork'):
                        if facts.get(key):
                            app[key] = facts[key]
        candidate = candidate_record(track, 'us', checked_at)
        if not candidate:
            return
        # Global human review remains authoritative for all storefronts.
        item = merge_candidate(previous.get(ident), candidate)
        previous[ident] = item
        if item['reviewStatus'] != 'pending':
            return
        if ident not in by_id:
            app = new_catalog_entry(candidate)
            catalog['apps'].append(app)
            by_id[ident] = app
        remember_listing(by_id[ident], track, 'us', checked_at)
        apply_candidate(by_id[ident], candidate)

    for offset in range(0, len(selected), BATCH_SIZE):
        if not remaining():
            break
        batch = selected[offset:offset + BATCH_SIZE]
        attempted += len(batch)
        params = urllib.parse.urlencode({'id': ','.join(map(str, batch)), 'country': 'us', 'entity': 'software'})
        data = request(APPLE_LOOKUP + '?' + params)
        if not isinstance(data, dict) or not isinstance(data.get('results'), list):
            continue
        coverage['lookupRequestsSucceeded'] += 1
        for track in data['results']:
            if not isinstance(track, dict) or positive_id(track.get('trackId')) not in batch:
                continue
            if track.get('kind') not in (None, 'software') or track.get('wrapperType') not in (None, 'software'):
                continue
            ident = int(track['trackId'])
            coverage['lookupReturned'] += 1
            tracks[ident] = track
            process(track)
    coverage['lookupAttempted'] = attempted
    _, queue['lookupCursorUS'] = rotate(pool, queue.get('lookupCursorUS', 0), attempted)

    # Page history covers only the current rotating page slice; never reuse CN notes.
    page_ids, _ = rotate(pool, queue.get('pageCursorUS', 0), page_limit)
    for ident in page_ids:
        if not remaining():
            break
        url = f'https://apps.apple.com/us/app/id{ident}'
        coverage['pagesAttempted'] += 1
        try:
            versions = page_versions(fetch_page(url))
            if not versions:
                coverage['pagesFailed'] += 1
                continue
            coverage['pagesParsed'] += 1
            for version, date, notes in versions[:30]:
                if not MENTION.search(notes):
                    continue
                track = tracks.get(ident)
                if not track:
                    params = urllib.parse.urlencode({'id': ident, 'country': 'us', 'entity': 'software'})
                    info = request(APPLE_LOOKUP + '?' + params)
                    track = next((t for t in (info or {}).get('results', [])
                                  if isinstance(t, dict) and t.get('trackId') == ident), None)
                if not track:
                    break
                page_track = {**track, 'version': version, 'currentVersionReleaseDate': date,
                              'releaseNotes': notes, 'trackViewUrl': url}
                claim = candidate_record(page_track, 'us', checked_at)
                if not claim:
                    continue
                claim['evidenceType'] = 'app_store_page_release_notes'
                item = merge_candidate(previous.get(ident), claim)
                previous[ident] = item
                if item['reviewStatus'] == 'pending':
                    if ident not in by_id:
                        app = new_catalog_entry(claim)
                        catalog['apps'].append(app)
                        by_id[ident] = app
                    apply_candidate(by_id[ident], claim)
                    # Do not present an old evidence version as today's store version.
                    latest_version, latest_date, _ = versions[0]
                    current = {**track, 'version': latest_version,
                               'currentVersionReleaseDate': latest_date, 'trackViewUrl': url}
                    remember_listing(by_id[ident], current, 'us', checked_at)
                    if primary_store(by_id[ident]) == 'us':
                        facts = by_id[ident].get('storeListings', {}).get('us', {})
                        for key in ('version', 'releaseDate', 'appStoreUrl', 'artwork', 'developer'):
                            if facts.get(key):
                                by_id[ident][key] = facts[key]
                break
        except (OSError, ValueError) as exc:
            coverage['pagesFailed'] += 1
            print(f'WARNING: US page {ident}: {exc}')
        if pause:
            time.sleep(.5)
    _, queue['pageCursorUS'] = rotate(pool, queue.get('pageCursorUS', 0), coverage['pagesAttempted'])
    coverage['timeBudgetReached'] = not remaining()
    # A successful HTTP response is not proof that every scheduled app was checked.
    coverage['status'] = ('failed' if not coverage['lookupRequestsSucceeded'] and not coverage['pagesParsed']
                          else 'partial' if coverage['timeBudgetReached'] or coverage['sourceRequestsFailed']
                          or coverage['pagesFailed'] or attempted > coverage['lookupReturned']
                          else 'completed')
    queue['coverageUS'] = coverage
    queue['candidates'] = sorted(previous.values(), key=lambda c: (c.get('reviewStatus') != 'pending', -int(c['itunesId'])))
    if coverage['status'] != 'failed':
        catalog['lastDiscoverySyncUS'] = checked_at
    print(f"US pool={len(pool)}; lookup returned={coverage['lookupReturned']}/{attempted}; "
          f"pages parsed={coverage['pagesParsed']}/{coverage['pagesAttempted']}; {coverage['status']}")
    return coverage
