"""Additive, ID-based storefront facts. Editorial verdicts stay untouched."""
from copy import deepcopy
from urllib.parse import urlsplit

STOREFRONTS = ('cn', 'us')


def primary_store(app):
    if app.get('storefront') in STOREFRONTS:
        return app['storefront']
    return 'us' if app.get('region') == '美国' else 'cn'


def evidence_store(app):
    try:
        region = urlsplit(app.get('duoDiscovery', {}).get('url', '')).path.split('/')[1]
        if region in STOREFRONTS:
            return region
    except (ValueError, IndexError):
        pass
    return primary_store(app)


def evidence_from(candidate):
    return {'type': candidate['evidenceType'], 'storefront': candidate['storefront'],
            'version': candidate['version'], 'excerpt': candidate['evidenceExcerpt'],
            'url': candidate['appStoreUrl'], 'date': candidate['releaseDate'][:10]}


def remember_listing(app, track, region, checked_at):
    from discover_duo_apps import safe_artwork, safe_apple_url
    if track.get('trackId') != app.get('itunesId') or region not in STOREFRONTS:
        return
    listings = app.setdefault('storeListings', {})
    old = listings.get(region, {})
    facts = {'storefront': region, 'name': str(track.get('trackName') or ''),
             'version': str(track.get('version') or ''),
             'releaseDate': str(track.get('currentVersionReleaseDate') or ''),
             'appStoreUrl': safe_apple_url(track.get('trackViewUrl')),
             'artwork': safe_artwork(track.get('artworkUrl512') or track.get('artworkUrl100')),
             'developer': str(track.get('artistName') or '')}
    if str(old.get('releaseDate', ''))[:10] > facts['releaseDate'][:10]:
        facts = old.copy()
    else:
        facts = {**old, **{k: v for k, v in facts.items() if v}}
    facts['checkedAt'] = checked_at
    listings[region] = facts


def remember_evidence(app, candidate):
    evidence = app.setdefault('storeDiscoveries', {})
    if app.get('duoDiscovery') and not evidence:
        evidence[evidence_store(app)] = deepcopy(app['duoDiscovery'])
    region = candidate['storefront']
    old = evidence.get(region, {})
    if old.get('date', '') > candidate['releaseDate'][:10]:
        return
    evidence[region] = evidence_from(candidate)
    # Keep the legacy card's primary evidence within its primary storefront.
    if region == primary_store(app):
        value = evidence[region].copy()
        value.pop('storefront', None)
        app['duoDiscovery'] = value


def merge_candidate(previous, candidate):
    """One global review decision; retain each storefront's separate evidence."""
    original = previous or {}
    evidence = deepcopy(original.get('storeEvidence', {}))
    if original and original.get('storefront') in STOREFRONTS:
        evidence.setdefault(original['storefront'], {k: v for k, v in original.items() if k != 'storeEvidence'})
    region = candidate['storefront']
    old = evidence.get(region, {})
    if old.get('releaseDate', '')[:10] <= candidate['releaseDate'][:10]:
        evidence[region] = {**old, **candidate}
    selected = evidence.get(original.get('storefront')) if original else evidence[region]
    if region == 'cn' and original.get('storefront') != 'cn':
        selected = evidence[region]
    machine_fields = ('itunesId', 'name', 'storefront', 'version', 'releaseDate',
                      'evidenceType', 'evidenceExcerpt', 'appStoreUrl', 'artwork',
                      'developer', 'storeCategory')
    selected = selected or candidate
    values = {key: selected[key] for key in machine_fields if key in selected}
    return {**original, **values, 'storeEvidence': evidence,
            'firstSeen': original.get('firstSeen') or candidate['firstSeen'],
            'lastSeen': candidate['lastSeen'],
            'reviewStatus': original.get('reviewStatus', 'pending')}
