import importlib.util
import unittest
import copy
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(BASE/'scripts'))
spec = importlib.util.spec_from_file_location('issueingest', BASE/'scripts/ingest_issue.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class IngestTest(unittest.TestCase):
    def sample(self, name='招商银行', url='https://apps.apple.com/cn/app/id392899425'):
        return {'issue': {'number':42, 'title':'[收录] 招商银行', 'body':
           f'### App 名称\n\n{name}\n\n### App Store 链接\n\n{url}\n\n### 应用分类\n\n金融理财\n\n### 主要地区\n\n中国大陆\n\n### 适配证据（如有）\n\n微博网友反馈'}}

    def test_sections(self):
        x=module.sections('### App 名称\n\n千问\n### App Store 链接\n\nhttps://apps.apple.com/cn/app/id1234567')
        self.assertEqual(x['App 名称'],'千问')

    def test_id_url(self):
        self.assertEqual(module.apple_id_from_url('https://apps.apple.com/cn/app/%E5%95%86%E6%88%B7/id392899425?foo=1'), (392899425,'cn'))
        self.assertIsNone(module.apple_id_from_url('https://apple.example.com/id392899425'))
        self.assertIsNone(module.apple_id_from_url('https://apps.apple.com/cn/search?term=ABC'))

    def test_ingest_new(self):
        event=self.sample()
        parsed=module.parse_issue(event,resolver=lambda id,country: {'trackId':id, 'trackName':'招商银行','kind':'software', 'artistName':'招商银行','artworkUrl100':'https://is1-ssl.mzstatic.com/image/thumb/icon.png'})
        data={'apps':[]}
        result=module.update_catalog(data,parsed,event['issue'],'VankerWu/iPhone-Duo-Apps','2026-10-26')
        self.assertEqual(result,'added')
        self.assertEqual(data['apps'][0]['itunesId'],392899425)
        self.assertEqual(data['apps'][0]['status'],'unverified')
        self.assertEqual(data['apps'][0]['artwork'],'https://is1-ssl.mzstatic.com/image/thumb/icon.png')
        self.assertEqual(data['apps'][0]['sourceUrl'],'https://github.com/VankerWu/iPhone-Duo-Apps/issues/42')

    def test_existing_no_promotion(self):
        event=self.sample()
        parsed=module.parse_issue(event,resolver=lambda id,country: {})
        data={'apps':[{'id':'test','name':'招商银行','itunesId':392899425,'status':'apple_featured','note':'苹果官方介绍'}]}
        result=module.update_catalog(data,parsed,event['issue'],'VankerWu/iPhone-Duo-Apps','2026-10-26')
        self.assertEqual(result,'existing-updated')
        self.assertEqual(data['apps'][0]['status'],'apple_featured')
        self.assertEqual(data['apps'][0]['note'],'苹果官方介绍')
        result=module.update_catalog(data,parsed,event['issue'],'VankerWu/iPhone-Duo-Apps','2026-10-26')
        self.assertEqual(result,'unchanged')

    def test_refuses_missing_store_and_no_lookup(self):
        event=self.sample(url='')
        with self.assertRaises(ValueError):
            module.parse_issue(event,resolver=lambda _id,country,name: None)

    def test_fallback_unique(self):
        event=self.sample('千问','')
        parsed=module.parse_issue(event,resolver=lambda id,country,name: (6466733523,{'trackName':'千问'}))
        self.assertEqual(parsed['itunesId'],6466733523)

    def test_sanitizes_artwork(self):
        self.assertEqual(module.apple_artwork({'artworkUrl100':'https://example.com/fake.png'}),'')

    def test_existing_simple_legacy_template(self):
        issue={'issue': {'number':3, 'title':'提交一款 iPhone Duo 适配应用', 'body':'## 应用名称\n千问\n\n## App Store 链接\nhttps://apps.apple.com/cn/app/id6466733523\n'}}
        parsed=module.parse_issue(issue,resolver=lambda id,country: None)
        self.assertEqual(parsed['name'],'千问')

if __name__=='__main__':unittest.main()
