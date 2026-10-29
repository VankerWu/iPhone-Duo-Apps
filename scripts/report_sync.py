#!/usr/bin/env python3
"""Compare against pre-refresh data; publish explicit, conservative run reports."""
import datetime as dt
import json
import os
import sys
from pathlib import Path
from store_categories import app_type, for_app, seed_categories


def build(before, after):
    def key(a):
        return str(a.get('itunesId') or a['id'])
    old = {key(a): a for a in before['apps']}
    old_ids = {a['id']: a for a in before['apps']}
    seed = seed_categories()
    result = {'time': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
              'added': [], 'updated': [], 'signals': []}
    for app in after['apps']:
        prev = old.get(key(app)) or old_ids.get(app['id'])
        item = {k: app.get(k, '') for k in ('id', 'name', 'version', 'appStoreUrl', 'status')}
        item.update(itunesId=app.get('itunesId'), appType=app_type(app, seed), category=for_app(app, seed).get('primaryGenreName', '分类待同步'))
        if prev is None:
            result['added'].append(item)
            app.setdefault('addedAt', result['time'])
        else:
            if app.get('version') and prev.get('version') != app['version']:
                result['updated'].append({**item, 'previousVersion': prev.get('version', '')})
        evidence = app.get('duoDiscovery')
        if evidence and evidence != (prev or {}).get('duoDiscovery'):
            result['signals'].append({**item, 'evidence': evidence})
    result['addedCounts'] = {kind: sum(a['appType'] == kind for a in result['added']) for kind in ('software', 'game', 'unknown')}
    return result


def render(report):
    lines = ['# 本轮抓取报告', report['time'], '', '新增收录、版本更新和适配线索分开统计；不代表本站实测。']
    coverage = report.get('coverageCN', {})
    if coverage:
        lines += ['', '## 国区扫描范围', f"候选池 {coverage['poolSize']} 个 ID；本轮计划检查 {coverage['lookupScheduled']} 个；分类榜单成功 {coverage['categoryFeedsSucceeded']}/{coverage['categoryFeedsAttempted']}。", '候选池不等于适配数量，未完成的部分后续轮询。']
        if 'gameFeedsAttempted' in coverage:
            lines += [f"其中游戏子分类榜单成功 {coverage['gameFeedsSucceeded']}/{coverage['gameFeedsAttempted']}。"]
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
    groups = [('software', '软件'), ('game', '游戏'), ('unknown', '类型待同步')]
    for kind, label in groups:
        items = [a for a in report['added'] if a.get('appType', 'unknown') == kind]
        lines += ['', f'## 新增{label}（{len(items)}）'] + ([f"- {a['name']}｜{a.get('category', '分类待同步')}" for a in items] or ['无。'])
    lines += ['', '## 可复制微博文案', '', 'iPhone Duo App 适配目录更新：']
    if report['added']:
        for kind, label in groups:
            items = [a for a in report['added'] if a.get('appType', 'unknown') == kind]
            if items:
                lines += [f'新增{label} {len(items)} 款：' + '、'.join(a['name'] for a in items) + '。']
        lines += ['自动发现的新增条目先进入待确认；人工审核结论单独标注。']
    else:
        lines += ['本轮没有新增收录 App。']
    lines += [f"另有 {len(report['updated'])} 款已有 App 版本资料更新；普通版本更新不代表新增适配。",
              'https://vankerwu.github.io/iPhone-Duo-Apps/']
    return '\n'.join(lines) + '\n'


def save_history(folder, report):
    path = folder / 'history.json'
    history = json.loads(path.read_text()) if path.exists() else []
    # Bootstrap with the last real report; never invent past additions.
    latest = folder / 'latest.json'
    if not history and latest.exists():
        history = [json.loads(latest.read_text())]
    history = [item for item in history if item.get('time') != report['time']]
    path.write_text(json.dumps([report] + history[:99], ensure_ascii=False, indent=2) + '\n')


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
    report['weiboText'] = content.split('## 可复制微博文案\n\n', 1)[1]
    save_history(folder, report)
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
