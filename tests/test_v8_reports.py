import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT/'scripts'))
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class V8Tests(unittest.TestCase):
    def test_version_history_is_scoped(self):
        mod = load('discover_duo_apps')
        text = '''<p>review: supports iPhone Duo</p><li><span><!-- HTML_TAG_START -->适配 iPhone Duo 折叠屏<!-- HTML_TAG_END --></span><div class="metadata svelte-1"><span>10.2.3</span><time datetime="2026-10-26">今天</time></div></li>'''
        self.assertEqual(mod.page_versions(text), [('10.2.3', '2026-10-26', '适配 iPhone Duo 折叠屏')])
        self.assertEqual(mod.page_versions('<p>review: supports iPhone Duo</p>'), [])

    def test_report_separates_metadata_and_new_claims(self):
        mod = load('report_sync')
        before = {'apps': [{'id': 'a', 'version': '1', 'name': 'Old'}]}
        after = {'apps': [{'id': 'a', 'version': '2', 'name': 'Old'},
                          {'id': 'b', 'version': '1', 'name': 'New', 'status': 'unverified'}]}
        report = mod.build(before, after)
        self.assertEqual([a['name'] for a in report['added']], ['New'])
        self.assertEqual([a['name'] for a in report['updated']], ['Old'])
        self.assertEqual(report['signals'], [])
        self.assertIn('addedAt', after['apps'][1])
        self.assertIn('本轮没有新增', mod.render(mod.build(after, after)))
        self.assertIn('待确认', mod.render(report))

    def test_repeat_same_evidence_is_not_a_new_signal(self):
        mod = load('report_sync')
        data = {'apps': [{'id': 'a', 'name': 'App', 'duoDiscovery': {'version': '1', 'excerpt': '适配'}}]}
        self.assertEqual(mod.build(data, data)['signals'], [])
