#!/usr/bin/env python3
"""Compare against pre-refresh data; publish explicit, conservative run reports."""
import datetime as dt
import json
import os
import sys
from pathlib import Path


def build(before, after):
    def key(a):
        return str(a.get('itunesId') or a['id'])
    old = {key(a): a for a in before['apps']}
    result = {'time': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
              'added': [], 'updated': [], 'signals': []}
    for app in after['apps']:
        prev = old.get(key(app))
        item = {k: app.get(k, '') for k in ('id', 'name', 'version', 'appStoreUrl', 'status')}
        if prev is None:
            result['added'].append(item)
            app.setdefault('addedAt', result['time'])
        else:
            if app.get('version') and prev.get('version') != app['version']:
                result['updated'].append({**item, 'previousVersion': prev.get('version', '')})
        evidence = app.get('duoDiscovery')
        if evidence and evidence != (prev or {}).get('duoDiscovery'):
            result['signals'].append({**item, 'evidence': evidence})
    return result


def render(report):
    lines = ['# 本轮抓取报告', report['time'], '', '新增收录、版本更新和适配线索分开统计；不代表本站实测。']
    coverage = report.get('coverageCN', {})
    if coverage:
        lines += ['', '## 国区扫描范围', f"候选池 {coverage['poolSize']} 个 ID；本轮计划检查 {coverage['lookupScheduled']} 个；分类榜单成功 {coverage['categoryFeedsSucceeded']}/{coverage['categoryFeedsAttempted']}。", '候选池不等于适配数量，未完成的部分后续轮询。']
    for key, title in [('added', '新增 App'), ('updated', '已有 App 版本更新'), ('signals', '新增或变化的适配线索')]:
        lines += ['', f'## {title}（{len(report[key])}）']
        for app in report[key]:
            name = app['name'].replace('\n', ' ')
            lines.append(f"- {name}｜{app.get('previousVersion', '') + ' → ' if key == 'updated' else ''}{app['version']}")
            if key == 'signals':
                e = app['evidence']
                lines += [f"  证据版本：{e.get('version', '')}；{e.get('excerpt', '').replace(chr(10), ' ')}", f"  {e.get('url', '')}"]
        if not report[key]:
            lines.append('无。')
    lines += ['', '## 可复制微博文案', '', 'iPhone Duo App 适配目录更新：']
    if report['added']:
        lines += [f"本次新增收录 {len(report['added'])} 款：" + '、'.join(a['name'] for a in report['added']) + '。']
        lines += ['新增条目先进入待确认，开发者适配声明与用户实测结论分别标注。']
    else:
        lines += ['本轮没有新增收录 App。']
    lines += [f"另有 {len(report['updated'])} 款已有 App 版本资料更新；普通版本更新不代表新增适配。",
              'https://vankerwu.github.io/iPhone-Duo-Apps/']
    return '\n'.join(lines) + '\n'


def main():
    before = json.loads(Path(sys.argv[1]).read_text())
    data = Path('docs/data/apps.json')
    after = json.loads(data.read_text())
    report = build(before, after)
    queue = Path('docs/data/duo-review-queue.json')
    if queue.exists():
        q = json.loads(queue.read_text())
        report['coverageCN'] = q.get('coverageCN', {})
    data.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n')
    folder = Path('docs/updates'); folder.mkdir(exist_ok=True)
    content = render(report)
    name = report['time'].replace(':', '-') + '.md'
    (folder/name).write_text(content)
    (folder/'latest.md').write_text(content)
    (folder/'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(content)
    print(content)


if __name__ == '__main__':
    main()
