import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from test_v8_reports import load

class UpgradeTests(unittest.TestCase):
    def test_priority_found_outside_all_charts(self):
        m=load('discover_duo_apps')
        catalog={'apps':[]};queue={'candidates':[], 'discoveryPoolCN':list(range(1,702))}
        requested=set()
        def fetch(url):
            if '/lookup?' in url:
                ids=set(map(int,parse_qs(urlparse(url).query)['id'][0].split(',')));requested.update(ids)
                return {'results':[{'trackId':1422581869,'trackName':'酷安','version':'16.7','releaseNotes':'适配 iPhone Duo','trackViewUrl':'https://apps.apple.com/cn/app/id1422581869'}] if 1422581869 in ids else []}
            if '/search?' in url:return {'results':[]}
            return {'feed':{'results':[], 'entry':[]}}
        m.discover(catalog,queue,fetch=fetch)
        self.assertTrue(m.priority_ids()<=requested)
        self.assertTrue(set(range(1,601))<=requested)
        self.assertEqual(catalog['apps'][0]['status'],'unverified')
        self.assertEqual(queue['coverageCN']['lookupReturned'],1)
        queue['candidates'][0]['reviewStatus']='rejected';catalog['apps']=[]
        m.discover(catalog,queue,fetch=fetch)
        self.assertEqual(catalog['apps'],[])

    def test_history_keeps_additions_after_empty_run(self):
        m=load('report_sync')
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);a={'time':'1','added':[{'name':'App'}]};b={'time':'2','added':[]}
            (folder/'latest.json').write_text(json.dumps(a))
            m.save_history(folder,b);m.save_history(folder,b)
            self.assertEqual(json.loads((folder/'history.json').read_text()),[b,a])
