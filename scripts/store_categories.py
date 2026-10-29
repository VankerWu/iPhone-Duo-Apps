"""CN Apple genre metadata, independent from editorial compatibility decisions.

Keep legacy category/status/evidence fields intact. An unavailable lookup does
not erase a previous classification and never guesses an app's type by name.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = json.loads((ROOT / 'docs/data/app-store-genres.json').read_text(encoding='utf-8'))
MAIN = TAXONOMY['main']
GAMES = TAXONOMY['games']
SEED = ROOT / 'docs/data/app-categories-cn.json'


def positive_id(value):
    return int(value) if not isinstance(value, bool) and str(value).isdigit() and int(value) > 0 else None


def from_track(track, country='cn'):
    if country != 'cn' or not isinstance(track, dict):
        return None
    primary = positive_id(track.get('primaryGenreId'))
    if not primary:
        return None
    raw_ids = track.get('genreIds') if isinstance(track.get('genreIds'), list) else []
    raw_names = track.get('genres') if isinstance(track.get('genres'), list) else []
    ids = list(dict.fromkeys([primary] + [ident for v in raw_ids
                                       if (ident := positive_id(v))]))
    labels = dict(zip(map(str, raw_ids), raw_names))
    def label(ident):
        return (MAIN.get(str(ident)) or GAMES.get(str(ident)) or {}).get('name') or str(labels.get(str(ident)) or (track.get('primaryGenreName') if ident == primary else '') or f'分类 {ident}')
    app_type = ('game' if primary == 6014 or str(primary) in GAMES else
                'software' if str(primary) in MAIN else 'unknown')
    return {'source': 'apple_lookup', 'storefront': 'cn', 'primaryGenreId': primary,
            'primaryGenreName': label(primary), 'genreIds': ids,
            'genres': [label(ident) for ident in ids], 'appType': app_type}


def apply(app, track, country='cn'):
    metadata = from_track(track, country)
    if not metadata:
        return False
    ident = positive_id(track.get('trackId'))
    if not ident or (app.get('itunesId') and positive_id(app['itunesId']) != ident):
        return False
    changed = app.get('storeCategory') != metadata
    app['storeCategory'] = metadata
    return changed


def seed_categories():
    return json.loads(SEED.read_text(encoding='utf-8')).get('apps', {}) if SEED.exists() else {}


def for_app(app, seed=None):
    metadata = app.get('storeCategory') or (seed or {}).get(str(app.get('itunesId')))
    if isinstance(metadata, dict) and metadata.get('storefront') == 'cn':
        return metadata
    return {}


def app_type(app, seed=None):
    value = for_app(app, seed).get('appType')
    return value if value in ('software', 'game') else 'unknown'
