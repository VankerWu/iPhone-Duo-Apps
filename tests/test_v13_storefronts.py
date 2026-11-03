"""Cross-storefront safety and bounded discovery integration checks."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from test_v8_reports import load
from test_discover_duo_apps import sample
import discover_us_apps as us
import storefront_data as facts
import store_categories


def listing(ident=900, notes='Added support for iPhone Duo.', version='2.0'):
    return {**sample(ident, f'US App {ident}', notes), 'version': version,
            'trackViewUrl': f'https://apps.apple.com/us/app/id{ident}',
            'primaryGenreId': 6007, 'primaryGenreName': 'Productivity',
            'genreIds': ['6007'], 'genres': ['Productivity']}


def transport(items):
    def fetch(url):
        if '/lookup?' in url:
            params = parse_qs(urlsplit(url).query)
            assert params['country'] == ['us'], url
            ids = set(map(int, params['id'][0].split(',')))
            return {'results': [item for item in items if item['trackId'] in ids]}
        if '/search?' in url:
            assert 'country=us' in url
            return {'results': []}
        assert '/us/' in url, url
        return {'feed': {'results': [{'id': str(item['trackId'])} for item in items], 'entry': []}}
    return fetch


class USStorefrontTests(unittest.TestCase):
    def run_scan(self, catalog, queue, items, **kwargs):
        return us.discover_us(catalog, queue, fetch=transport(items), page_limit=0,
                             checked_at='2026-11-04T00:00:00+00:00', **kwargs)

    def test_us_only_app_is_pending_with_official_category(self):
        catalog, queue = {'apps': []}, {'candidates': []}
        self.run_scan(catalog, queue, [listing()])
        self.assertEqual(len(catalog['apps']), 1)
        app = catalog['apps'][0]
        self.assertEqual((app['status'], app['region'], app['storefront']), ('unverified', '美国', 'us'))
        self.assertEqual(app['storeCategory']['appType'], 'software')
        self.assertEqual(app['storeCategory']['storefront'], 'us')
        self.assertEqual(app['storeListings']['us']['version'], '2.0')
        self.assertIn('us', app['storeDiscoveries'])

    def test_same_id_does_not_overwrite_cn_editorial_or_primary_metadata(self):
        cn = load('discover_duo_apps')
        app = cn.new_catalog_entry(cn.candidate_record(sample(900, '人工中文名', '适配 iPhone Duo'), 'cn', 'first'))
        app.update(status='community_verified', note='保留人工批注', sourceLabel='实测',
                   sourceUrl='https://example.org', verifiedDate='2026-10-01')
        app['storeCategory'] = store_categories.from_track({**listing(), 'primaryGenreId': 6002}, 'cn')
        original = copy.deepcopy(app)
        catalog, queue = {'apps': [app]}, {'candidates': []}
        self.run_scan(catalog, queue, [listing(version='9.0')])
        self.assertEqual(len(catalog['apps']), 1)
        for field in original:
            self.assertEqual(app[field], original[field], field)
        self.assertEqual(app['storeListings']['us']['version'], '9.0')
        self.assertIn('cn', app['storeDiscoveries'])
        self.assertIn('us', app['storeDiscoveries'])
        report = load('report_sync').build({'apps': [original]}, catalog)
        self.assertEqual(report['added'], [])
        self.assertEqual(report['updated'], [])
        self.assertEqual([a['storefront'] for a in report['signals']], ['us'])
        self.assertEqual(report['storeUpdates'][0]['change'], 'first_seen')

    def test_rejected_id_is_not_republished_in_another_region(self):
        catalog = {'apps': []}
        queue = {'candidates': [{'itunesId': 900, 'storefront': 'cn', 'version': '5',
                                'releaseDate': '2026-11-01', 'firstSeen': 'first',
                                'reviewStatus': 'rejected', 'reviewer': 'owner',
                                'reviewNote': '证据不足'}]}
        self.run_scan(catalog, queue, [listing()])
        self.assertEqual(catalog['apps'], [])
        record = queue['candidates'][0]
        self.assertEqual(record['reviewStatus'], 'rejected')
        self.assertEqual(record['reviewer'], 'owner')
        self.assertEqual(record['reviewNote'], '证据不足')
        self.assertIn('us', record['storeEvidence'])
        self.assertEqual(record['storefront'], 'cn')

    def test_pool_is_not_a_public_catalog_and_persists_off_chart_ids(self):
        catalog = {'apps': []}; queue = {'candidates': [], 'discoveryPoolUS': [701]}
        ordinary = [listing(901, 'Bug fixes.'), listing(902, 'iPhone Duo not supported yet.'),
                    listing(903, 'iPhone Duo support coming soon.')]
        self.run_scan(catalog, queue, ordinary)
        self.assertEqual(catalog['apps'], [])
        self.assertEqual(queue['discoveryPoolUS'], [701, 901, 902, 903])
        self.assertEqual(queue['candidates'], [])

    def test_us_state_never_moves_cn_cursors_or_pool(self):
        queue = {'candidates': [], 'discoveryPoolCN': [1, 2], 'lookupCursorCN': 7,
                 'genreCursorCN': 5, 'gameGenreCursorCN': 2, 'pageCursor': 11}
        original = copy.deepcopy(queue)
        self.run_scan({'apps': []}, queue, [listing()])
        for field in original:
            if field != 'candidates':
                self.assertEqual(queue[field], original[field])
        self.assertNotIn(1, queue['discoveryPoolUS'])

    def test_us_failure_does_not_claim_fresh_sync(self):
        catalog = {'apps': []}; queue = {'candidates': []}
        result = us.discover_us(catalog, queue, fetch=lambda _: None, page_limit=0)
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('lastDiscoverySyncUS', catalog)

    def test_expired_budget_does_not_advance_lookup_cursor(self):
        catalog = {'apps': []}; queue = {'candidates': [], 'discoveryPoolUS': [1, 2], 'lookupCursorUS': 1}
        times = iter([0] + [1000] * 100)
        urls = []
        us.discover_us(catalog, queue, fetch=lambda url: urls.append(url), clock=lambda: next(times), max_seconds=1)
        self.assertEqual(urls, [])
        self.assertEqual(queue['lookupCursorUS'], 1)
        self.assertTrue(queue['coverageUS']['timeBudgetReached'])

    def test_us_page_history_with_lagging_lookup_keeps_version_scope(self):
        current = listing(version='1.0', notes='Bug fixes.')
        markup = '''<li><span><!-- HTML_TAG_START -->Bug fixes<!-- HTML_TAG_END --></span><div class="metadata x"><span>3.0</span><time datetime="2026-11-03">now</time></div></li><li><span><!-- HTML_TAG_START -->Support for iPhone Duo<!-- HTML_TAG_END --></span><div class="metadata x"><span>2.0</span><time datetime="2026-11-01">then</time></div></li>'''
        catalog, queue = {'apps': []}, {'candidates': []}
        result = us.discover_us(catalog, queue, fetch=transport([current]), fetch_page=lambda url: markup, page_limit=1)
        self.assertEqual(result['pagesParsed'], 1)
        app = catalog['apps'][0]
        self.assertEqual(app['version'], '3.0')
        self.assertEqual(app['duoDiscovery']['version'], '2.0')
        self.assertEqual(app['storeDiscoveries']['us']['type'], 'app_store_page_release_notes')
        self.assertEqual(app['storeListings']['us']['version'], '3.0')

    def test_us_listing_does_not_migrate_primary_category_back_from_cn(self):
        app = {'itunesId': 900, 'storefront': 'us', 'version': '9.0', 'releaseDate': '2026-11-03', 'appStoreUrl': 'https://apps.apple.com/us/app/id900'}
        refresh = load('refresh_metadata')
        refresh.apply_metadata(app, {**listing(version='1.0'), 'trackViewUrl':'https://apps.apple.com/cn/app/id900'}, 'cn')
        self.assertEqual(app['version'], '9.0')
        self.assertIn('/us/', app['appStoreUrl'])
        self.assertIn('cn', app['storeListings'])

    def test_us_games_use_official_ids(self):
        app = listing()
        app.update(primaryGenreId=6014, genreIds=['6014', '7001'], genres=['Games', 'Action'])
        catalog, queue = {'apps': []}, {'candidates': []}
        self.run_scan(catalog, queue, [app])
        self.assertEqual(catalog['apps'][0]['storeCategory']['appType'], 'game')

    def test_repeat_us_claim_does_not_create_duplicate_report_signals(self):
        catalog, queue = {'apps': []}, {'candidates': []}
        self.run_scan(catalog, queue, [listing()])
        before = copy.deepcopy(catalog)
        self.run_scan(catalog, queue, [listing()])
        report = load('report_sync').build(before, catalog)
        self.assertEqual(report['added'], [])
        self.assertEqual(report['updated'], [])
        self.assertEqual(report['signals'], [])
        self.assertEqual(report['storeUpdates'], [])

    def test_cn_run_retains_us_evidence_and_review_fields(self):
        cn = load('discover_duo_apps')
        original = cn.candidate_record(sample(900, 'CN', '适配 iPhone Duo'), 'cn', 'first')
        original.update(reviewer='owner', reviewNote='人工保留')
        combined = facts.merge_candidate(original, cn.candidate_record(listing(version='4.0'), 'us', 'second'))
        combined = facts.merge_candidate(combined, cn.candidate_record(sample(900, 'CN', '适配 iPhone Duo'), 'cn', 'third'))
        self.assertEqual(combined['storefront'], 'cn')
        self.assertEqual(combined['storeEvidence']['us']['version'], '4.0')
        self.assertEqual(combined['reviewNote'], '人工保留')
        self.assertEqual(combined['firstSeen'], 'first')

    def test_later_review_edits_are_not_reverted_from_old_evidence_snapshots(self):
        cn = load('discover_duo_apps')
        first = cn.candidate_record(sample(900, 'CN', '适配 iPhone Duo'), 'cn', 'first')
        first.update(reviewer='old owner', reviewNote='old note')
        combined = facts.merge_candidate(first, cn.candidate_record(listing(), 'us', 'second'))
        combined.update(reviewer='current owner', reviewNote='new manual note', reviewedAt='today')
        final = facts.merge_candidate(combined, cn.candidate_record(listing(), 'us', 'third'))
        self.assertEqual(final['reviewer'], 'current owner')
        self.assertEqual(final['reviewNote'], 'new manual note')
        self.assertEqual(final['reviewedAt'], 'today')

    def test_failed_us_scan_rolls_back_its_partial_mutations(self):
        self.check_cli_partial('us')

    def test_failed_cn_scan_still_runs_us(self):
        self.check_cli_partial('cn')

    def check_cli_partial(self, failed):
        cn = load('discover_duo_apps')
        with tempfile.TemporaryDirectory() as folder:
            catalog = Path(folder)/'apps.json'; queue = Path(folder)/'queue.json'
            original = {'apps': [{'id':'curated','name':'保留','status':'apple_featured','note':'人工备注'}]}
            catalog.write_text(json.dumps(original)); queue.write_text(json.dumps({'candidates': []}))
            def chinese(c, q, **kwargs):
                c['cnRun'] = True
                if failed == 'cn':
                    c['corruption'] = 'must roll back'
                    raise RuntimeError('CN unavailable')
            def american(c, q, **kwargs):
                c['usRun'] = True
                if failed == 'us':
                    c['corruption'] = 'must roll back'
                    raise RuntimeError('US unavailable')
                return {'status':'completed'}
            argv = ['discover_duo_apps.py','--catalog',str(catalog),'--queue',str(queue),'--storefronts','cn','us']
            with patch('sys.argv',argv), patch.object(cn,'discover',chinese), patch.object(cn,'check_pages'), patch.object(us,'discover_us',american):
                cn.main()
            saved = json.loads(catalog.read_text())
            self.assertEqual(saved['apps'], original['apps'])
            self.assertNotIn('corruption', saved)
            self.assertIn('usRun' if failed == 'cn' else 'cnRun', saved)
            self.assertEqual(json.loads(queue.read_text())['lastScanOutcomes']['storefronts'][failed], 'failed')
