"""Offline regression tests for conservative App Store signal discovery."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'discover_duo_apps.py'
import sys
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('discover_duo_apps', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample(id, name, notes):
    return {
        'kind': 'software', 'wrapperType': 'software',
        'trackId': id, 'trackName': name, 'releaseNotes': notes,
        'version': '2.0', 'artistName': 'Official Publisher',
        'currentVersionReleaseDate': '2026-10-25T00:00:00Z',
        'trackViewUrl': f'https://apps.apple.com/cn/app/id{id}',
        'artworkUrl100': f'https://is1-ssl.mzstatic.com/image/thumb/fake/{id}/100x100bb.png',
    }


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            'id': 'existing-1', 'name': 'VerifiedApp', 'status': 'community_verified',
            'note': '经人工测试多姿态', 'sourceUrl': 'https://example.org/report',
            'sourceDate': '2026-10-20', 'itunesId': 10, 'storefront': 'cn',
        }
        self.catalog = {'apps': [self.original]}
        self.queue = module.initial_review_queue()
        self.items = [
            sample(10, 'VerifiedApp', 'Support for iPhone Duo landscape experience.'),
            sample(22, 'NewApp', 'This update adds iPhone Duo split-screen layout.'),
            sample(23, 'OtherApp', 'Bug fixes and performance improvements.'),
            sample(24, 'AnotherApp', 'General support for duo modes.'),
            sample(25, 'MisleadingApp', 'iPhone Duo not supported yet.'),
        ]

    def fetcher(self, url):
        self.assertNotIn('/us/', url)
        self.assertNotIn('country=us', url)
        if '/rss/' in url:
            return {'feed': {'entry': []}}
        if '/api/v2/cn/apps/' in url:
            return {'feed': {'results': [{'id': str(x['trackId'])} for x in self.items]}}
        if '/api/v2/us/apps/' in url:
            return {'feed': {'results': []}}
        if '/search?' in url:
            return {'results': []}
        if '/lookup?' in url:
            from urllib.parse import parse_qs, urlsplit
            q = parse_qs(urlsplit(url).query)
            ids = {int(x) for x in q['id'][0].split(',')}
            if q['country'][0] != 'cn':
                return {'results': []}
            return {'results': [x for x in self.items if x['trackId'] in ids]}
        self.fail('Unexpected remote URL: ' + url)

    def test_find_candidates_not_unrelated_chart_apps(self):
        inserted, signals, responses = module.discover(
            self.catalog, self.queue, fetch=self.fetcher,
            checked_at='2026-10-26T00:00:00+00:00')
        self.assertEqual((inserted, signals), (1, 2))
        self.assertGreater(responses, 0)
        self.assertEqual(len(self.catalog['apps']), 2)
        self.assertEqual({x['itunesId'] for x in self.queue['candidates']}, {10, 22})
        new = next(x for x in self.catalog['apps'] if x['itunesId'] == 22)
        self.assertEqual(new['status'], 'unverified')
        self.assertEqual(new['category'], '分类待同步')
        self.assertTrue(new['artwork'].startswith('https://is1-ssl.mzstatic.com'))
        self.assertEqual(self.original['status'], 'community_verified')
        self.assertEqual(self.original['note'], '经人工测试多姿态')
        self.assertEqual(self.original['sourceUrl'], 'https://example.org/report')
        self.assertEqual(self.original['sourceDate'], '2026-10-20')

    def test_repeat_no_duplicate_and_keep_first_seen(self):
        module.discover(self.catalog, self.queue, fetch=self.fetcher,
                        checked_at='2026-10-25T00:00:00+00:00')
        module.discover(self.catalog, self.queue, fetch=self.fetcher,
                        checked_at='2026-10-26T00:00:00+00:00')
        self.assertEqual(len(self.catalog['apps']), 2)
        self.assertEqual(len(self.queue['candidates']), 2)
        for r in self.queue['candidates']:
            self.assertEqual(r['firstSeen'], '2026-10-25T00:00:00+00:00')
            self.assertEqual(r['lastSeen'], '2026-10-26T00:00:00+00:00')

    def test_search_discovers_app_outside_charts(self):
        def fetch(url):
            if '/api/v2/' in url:
                return {'feed': {'results': []}}
            if '/search?' in url:
                return {'results': [{'trackId': 22}]}
            return self.fetcher(url)
        module.discover(self.catalog, self.queue, fetch=fetch)
        self.assertIn(22, [a['itunesId'] for a in self.catalog['apps']])

    def test_review_fields_and_rejected_decision_survive(self):
        self.queue['candidates'] = [{
            'itunesId': 22, 'reviewStatus': 'rejected',
            'reviewer': 'owner', 'reviewNote': '不符合', 'firstSeen': '2026-01-01'}]
        module.discover(self.catalog, self.queue, fetch=self.fetcher)
        reviewed = next(c for c in self.queue['candidates'] if c['itunesId'] == 22)
        self.assertEqual(reviewed['reviewNote'], '不符合')
        self.assertEqual(reviewed['reviewer'], 'owner')
        self.assertEqual(reviewed['firstSeen'], '2026-01-01')
        self.assertNotIn(22, [a['itunesId'] for a in self.catalog['apps']])

    def test_preserve_pending_app_human_note(self):
        self.original.update(status='unverified', note='列入观察名单，人工批注')
        module.discover(self.catalog, self.queue, fetch=self.fetcher)
        self.assertEqual(self.original['note'], '列入观察名单，人工批注')

    def test_negative_and_future_mentions_do_not_publish(self):
        for notes in ('iPhone Duo not supported yet.', '暂不支持 iPhone Duo',
                      'iPhone Duo support coming soon', '计划支持 iPhone Duo', 'Read our iPhone Duo news',
                      'Bug fixes for all devices'):
            with self.subTest(notes=notes):
                self.assertIsNone(module.candidate_record(sample(22, 'App', notes), 'cn', 'now'))

    def test_chart_success_lookup_failure_is_not_successful_sync(self):
        def fetch(url):
            if '/lookup?' in url:
                return None
            return self.fetcher(url)
        with self.assertRaises(RuntimeError):
            module.discover(self.catalog, self.queue, fetch=fetch)
        self.assertNotIn('lastDiscoverySync', self.catalog)

    def test_untrusted_url_rejected(self):
        self.assertEqual(module.safe_apple_url('https://bad.tld/app/id22'), '')
        self.assertEqual(module.safe_apple_url('javascript:alert(1)'), '')
        self.assertEqual(module.safe_artwork('https://notmzstatic.com/img.png'), '')
        self.assertIsNone(module.candidate_record({
            **sample(22, 'NewApp', 'New iPhone Duo layout.'),
            'trackViewUrl': 'https://evil.example/payload',
        }, 'cn', '2026-10-26'))

    def test_no_data_raises_without_writing(self):
        with self.assertRaises(RuntimeError):
            module.discover(self.catalog, self.queue, fetch=lambda _: None)

    def test_does_not_equate_new_version_with_compatibility(self):
        self.assertFalse(module.MENTION.search('Foldable improvements and optimizations'))
        self.assertFalse(module.MENTION.search('Duo is a new brand of speakers'))
        self.assertTrue(module.MENTION.search('兼容 iPhone Duo 的折叠显示方式'))


if __name__ == '__main__':
    unittest.main()
