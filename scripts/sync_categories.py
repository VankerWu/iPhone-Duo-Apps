#!/usr/bin/env python3
"""Optional category-only refresh. Never rewrites apps.json or review records."""
import datetime as dt
import json
import urllib.parse
from pathlib import Path
from refresh_metadata import get_json
from store_categories import ROOT, SEED, from_track, positive_id, seed_categories
import time


def main():
    catalog = json.loads((ROOT / 'docs/data/apps.json').read_text(encoding='utf-8'))
    ids = sorted({ident for a in catalog['apps'] if (ident := positive_id(a.get('itunesId')))})
    categories = seed_categories()
    successes = 0
    for offset in range(0, len(ids), 30):
        batch = ids[offset:offset+30]
        url = 'https://itunes.apple.com/lookup?' + urllib.parse.urlencode({'id': ','.join(map(str, batch)), 'country': 'cn', 'entity': 'software'})
        payload = get_json(url, retries=1)
        for track in (payload or {}).get('results', []):
            if track.get('trackId') not in batch:
                continue
            metadata = from_track(track)
            if metadata:
                categories[str(track['trackId'])] = metadata
                successes += 1
        time.sleep(3.1)
    if not successes:
        raise RuntimeError('No Apple categories returned; category cache left unchanged.')
    result = {'source': 'Apple Lookup API', 'storefront': 'cn', 'time': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'apps': categories}
    SEED.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'CN category-only refresh: {successes}/{len(ids)} returned; catalog and review data untouched.')


if __name__ == '__main__':
    main()
