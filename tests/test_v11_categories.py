"""Behavior checks for classifications, discovery, and report safety."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_v8_reports import load
import store_categories as categories
from test_discover_duo_apps import sample


def game(ident=987654321):
    return {**sample(ident, '测试游戏', '适配 iPhone Duo 内屏布局。'),
            'primaryGenreId':6014, 'primaryGenreName':'Games',
            'genreIds':['6014','6016','7001','7017'], 'genres':['游戏','娱乐','动作','策略']}


class CategoriesTests(unittest.TestCase):
    def test_official_primary_and_secondary(self):
        data=categories.from_track(game())
        self.assertEqual(data['appType'],'game')
        self.assertEqual(data['genres'],['游戏','娱乐','动作','策略'])
        self.assertEqual(data['genreIds'],[6014,6016,7001,7017])
        self.assertEqual(categories.from_track({**game(),'primaryGenreId':6008})['appType'],'software')

    def test_names_never_determine_type(self):
        self.assertIsNone(categories.from_track({'trackName':'王者荣耀 游戏'}))
        self.assertEqual(categories.app_type({'name':'游戏','category':'新适配线索'}),'unknown')
        self.assertIsNone(categories.from_track(game(),'us'))

    def test_preserves_human_fields_and_missing_metadata(self):
        app={'itunesId':987654321,'category':'人工分类','status':'community_verified',
             'note':'人工实测','sourceUrl':'https://example.org','verifiedDate':'2026-10-01'}
        before=copy.deepcopy(app)
        categories.apply(app,game())
        self.assertEqual({k:app[k] for k in before},before)
        original=copy.deepcopy(app)
        self.assertFalse(categories.apply(app,{'trackId':987654321}))
        self.assertFalse(categories.apply(app,game(10)))
        self.assertEqual(app,original)

    def test_known_app_category_refresh_despite_older_api_version(self):
        m=load('refresh_metadata')
        app={'itunesId':987654321,'version':'99','releaseDate':'2026-10-29','status':'apple_featured','category':'原分类'}
        m.apply_metadata(app,game())
        self.assertEqual(app['version'],'99')
        self.assertEqual(app['storeCategory']['appType'],'game')
        self.assertEqual(app['status'],'apple_featured')

    def test_all_game_subcategories_rotate_without_starving_software(self):
        m=load('discover_duo_apps');catalog={'apps':[]};queue={'candidates':[]};seen=set()
        def fetch(url):
            if '/rss/' in url:
                genre=int(url.split('/genre=')[1].split('/')[0]);seen.add(genre)
                return {'feed':{'entry':[]}}
            if '/lookup?' in url:return {'results':[]}
            if '/search?' in url:return {'results':[]}
            return {'feed':{'results':[]}}
        for _ in range(4):m.discover(catalog,queue,fetch=fetch)
        self.assertTrue(set(m.GAME_GENRES)<=seen)
        self.assertTrue(set(m.GENRES)<=seen)
        self.assertEqual(queue['coverageCN']['gameFeedsAttempted'],12)

    def test_game_evidence_required_and_decisions_preserved(self):
        m=load('discover_duo_apps')
        self.assertIsNone(m.candidate_record({**game(),'releaseNotes':'修复问题，提升性能'},'cn','now'))
        item=m.candidate_record(game(),'cn','now');entry=m.new_catalog_entry(item)
        self.assertEqual(entry['storeCategory']['appType'],'game')
        self.assertEqual(entry['status'],'unverified')
        entry.update(status='community_verified',note='人工确认')
        m.apply_candidate(entry,item)
        self.assertEqual(entry['status'],'community_verified')
        self.assertEqual(entry['note'],'人工确认')

    def test_reports_separate_games_software_and_unknown_and_id_resolution(self):
        m=load('report_sync')
        original={'id':'existing','name':'原有应用','version':'1'}
        after={'apps':[{**original,'itunesId':123},
            {'id':'game','name':'新游戏','version':'1','status':'unverified','storeCategory':categories.from_track(game())},
            {'id':'software','name':'新软件','version':'1','storeCategory':categories.from_track({**game(),'primaryGenreId':6002})},
            {'id':'unknown','name':'待分类应用','version':'1'}]}
        report=m.build({'apps':[original]},after)
        self.assertEqual(report['addedCounts'],{'software':1,'game':1,'unknown':1})
        text=m.render(report)
        self.assertIn('新增游戏 1 款：新游戏',text)
        self.assertIn('新增软件 1 款：新软件',text)
        self.assertIn('类型待同步',text)
        self.assertNotIn('原有应用',text)

    def test_game_from_manual_issue_is_pending(self):
        m=load('ingest_issue');catalog={'apps':[]}
        record={'itunesId':987654321,'track':game(),'name':'新游戏','category':'其他应用','region':'中国大陆','storefront':'cn'}
        m.update_catalog(catalog,record,{'number':1},'test/repo','2026-10-29')
        self.assertEqual(catalog['apps'][0]['storeCategory']['appType'],'game')
        self.assertEqual(catalog['apps'][0]['status'],'unverified')

    def test_report_cli_keeps_catalog_and_writes_history(self):
        m=load('report_sync')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'docs/data').mkdir(parents=True)
            old={'apps':[{'id':'old','name':'原有应用','category':'人工','status':'apple_featured','note':'实测原文'}]}
            current=copy.deepcopy(old);current['apps'].append({'id':'new','name':'新游戏','version':'1','status':'unverified','storeCategory':categories.from_track(game())})
            (root/'before.json').write_text(json.dumps(old));(root/'docs/data/apps.json').write_text(json.dumps(current))
            with patch('sys.argv',['report_sync.py',str(root/'before.json')]):
                import os
                previous=os.getcwd();os.chdir(root)
                try:m.main()
                finally:os.chdir(previous)
            latest=json.loads((root/'docs/updates/latest.json').read_text())
            saved=json.loads((root/'docs/data/apps.json').read_text())
            self.assertEqual(latest['addedCounts']['game'],1)
            self.assertEqual(saved['apps'][0],old['apps'][0])
            self.assertTrue((root/'docs/updates/history.json').exists())
