import importlib.util
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
spec = importlib.util.spec_from_file_location('cn_discover', Path(__file__).resolve().parents[1]/'scripts/discover_duo_apps.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class ChinaCoverage(unittest.TestCase):
    def test_rotating_categories_cover_all(self):
        seen = set(); cursor = 0
        for _ in range((len(m.GENRES)+7)//8):
            selected, cursor = m.rotate(m.GENRES, cursor, 8)
            seen.update(selected)
        self.assertEqual(seen, set(m.GENRES))

    def test_pool_survives_chart_exit_and_checks_only_cn(self):
        catalog = {'apps': []}; queue = {'candidates': [], 'discoveryPoolCN': [777]}
        urls = []
        def fetch(url):
            urls.append(url)
            if '/lookup?' in url: return {'results': []}
            if '/rss/' in url:
                return {'feed': {'entry': [{'id': {'attributes': {'im:id': '888'}}}]}}
            if '/search?' in url: return {'results': []}
            return {'feed': {'results': []}}
        m.discover(catalog, queue, fetch=fetch)
        self.assertEqual(queue['discoveryPoolCN'], [777, 888])
        self.assertEqual(catalog['apps'], [])
        self.assertTrue(any('777%2C888' in u for u in urls))
        self.assertFalse(any('/us/' in u or 'country=us' in u for u in urls))

    def test_rotating_pool_is_bounded(self):
        values = list(range(1500)); cursor = 0; seen = set()
        for _ in range((len(m.GENRES)+7)//8):
            batch, cursor = m.rotate(values, cursor, 600)
            self.assertEqual(len(batch), 600); seen.update(batch)
        self.assertEqual(seen, set(values))

    def test_category_malformed_entries(self):
        self.assertEqual(m.category_ids({'feed': {'entry': [{'id': {'attributes': {'im:id': '123'}}}, {}, {'id': {'attributes': {'im:id': 'bad'}}}]}}), {123})
