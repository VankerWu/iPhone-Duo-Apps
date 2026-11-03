#!/usr/bin/env python3
"""Compare against pre-refresh data; publish explicit, conservative run reports."""
import datetime as dt
import json
import os
import sys
from pathlib import Path
from storefront_data import primary_store, evidence_store
from store_categories import app_type, for_app, seed_categories


def build(before, after):
    def key(a):
        return str(a.get('itunesId') or a['id'])
    old = {key(a): a for a in before['apps']}
    old_ids = {a['id']: a for a in before['apps']}
    seed = seed_categories()
    result = {'time': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
              'added': [], 'updated': [], 'signals': [], 'storeUpdates': []}
    for app in after['apps']:
        prev = old.get(key(app)) or old_ids.get(app['id'])
        item = {k: app.get(k, '') for k in ('id', 'name', 'version', 'appStoreUrl', 'status')}
        item.update(storefront=primary_store(app), storefronts=sorted(set(app.get('storeListings', {})) | {primary_store(app)}))
        item.update(itunesId=app.get('itunesId'), appType=app_type(app, seed), category=for_app(app, seed).get('primaryGenreName', '分类待同步'))
        if prev is None:
            result['added'].append(item)
            app.setdefault('addedAt', result['time'])
        else:
            if app.get('version') and prev.get('version') != app['version']:
                result['updated'].append({**item, 'previousVersion': prev.get('version', '')})
        if prev is not None:
            for region, listing in app.get('storeListings', {}).items():
                old_listing = prev.get('storeListings', {}).get(region)
                # Migrate legacy primary metadata without reporting it as a new region.
                if old_listing is None and region == primary_store(prev):
                    old_listing = prev
                if old_listing is None or (listing.get('version') and listing['version'] != old_listing.get('version')):
                    result['storeUpdates'].append({**item, 'storefront': region,
                        'version': listing.get('version', ''), 'appStoreUrl': listing.get('appStoreUrl', ''),
                        'previousVersion': (old_listing or {}).get('version', ''),
                        'change': 'version' if old_listing else 'first_seen'})
        def evidence_map(record):
            evidence = dict((record or {}).get('storeDiscoveries', {}))
            if (record or {}).get('duoDiscovery'):
                evidence.setdefault(evidence_store(record), record['duoDiscovery'])
            return {region: {k: v for k, v in claim.items() if k != 'storefront'}
                    for region, claim in evidence.items()}
        old_evidence = evidence_map(prev)
        for region, claim in evidence_map(app).items():
            if claim != old_evidence.get(region):
                result['signals'].append({**item, 'storefront': region,
                    'appStoreUrl': claim.get('url', item['appStoreUrl']), 'evidence': claim})
    result['addedCounts'] = {kind: sum(a['appType'] == kind for a in result['added']) for kind in ('software', 'game', 'unknown')}
    return result


def render(report):
    lines = ['# 本轮抓取报告', report['time'], '', '新增收录、版本更新和适配线索分开统计；不代表本站实测。']
    for region, title in (('CN', '国区'), ('US', '美区')):
        coverage = report.get('coverage' + region, {})
        outcome = report.get('scanOutcomes', {}).get('storefronts', {}).get(region.lower())
        if outcome == 'failed':
            lines += ['', f'## {title}扫描范围', '本轮扫描失败；保留此前数据，未报告该地区同步成功。']
            continue
        if coverage:
            lines += ['', f'## {title}扫描范围', f"候选池 {coverage['poolSize']} 个 ID；本轮计划检查 {coverage['lookupScheduled']} 个；分类榜单成功 {coverage['categoryFeedsSucceeded']}/{coverage['categoryFeedsAttempted']}。", '候选池不等于适配数量，未完成的部分后续轮询。']
            if 'gameFeedsAttempted' in coverage:
                lines += [f"其中游戏子分类榜单成功 {coverage['gameFeedsSucceeded']}/{coverage['gameFeedsAttempted']}。"]
            if region == 'US':
                lines += [f"Lookup 返回 {coverage.get('lookupReturned', 0)}/{coverage.get('lookupAttempted', 0)} 个条目；网页解析 {coverage.get('pagesParsed', 0)}/{coverage.get('pagesAttempted', 0)}。",
                          '各地区的版本说明独立保存；美区声明不代表国区已适配。']
                if coverage.get('status') == 'partial':
                    lines += ['本轮部分计划目标未返回资料或来源未完成；保留候选继续轮询，不据此推断已下架或已适配。']
                if coverage.get('timeBudgetReached'):
                    lines += ['本轮达到时间预算，其余候选下轮继续。']
    for key, title in [('added', '新增 App'), ('updated', '已有 App 版本更新'), ('signals', '新增或变化的适配线索')]:
        lines += ['', f'## {title}（{len(report[key])}）']
        for app in report[key]:
            name = app['name'].replace('\n', ' ')
            region_label = {'cn': '国区', 'us': '美区'}.get(app.get('storefront'), '')
            lines.append(f"- {name}{'〔' + region_label + '〕' if region_label else ''}｜{app.get('previousVersion', '') + ' → ' if key == 'updated' else ''}{app['version']}")
            if key == 'signals':
                e = app['evidence']
                lines += [f"  证据版本：{e.get('version', '')}；{e.get('excerpt', '').replace(chr(10), ' ')}", f"  {e.get('url', '')}"]
        if not report[key]:
            lines.append('本轮没有新增收录 App。' if key == 'added' else '无。')
    if report.get('storeUpdates'):
        lines += ['', '## 地区商店资料变化（不等于新增 App 或已适配）']
        for app in report['storeUpdates']:
            label = '国区' if app['storefront'] == 'cn' else '美区'
            change = '首次获取该地区资料' if app['change'] == 'first_seen' else f"{app['previousVersion']} → {app['version']}"
            lines.append(f"- {app['name']}〔{label}〕：{change}")
    groups = [('software', '软件'), ('game', '游戏'), ('unknown', '类型待同步')]
    for kind, label in groups:
        items = [a for a in report['added'] if a.get('appType', 'unknown') == kind]
        lines += ['', f'## 新增{label}（{len(items)}）'] + ([f"- {a['name']}｜{a.get('category', '分类待同步')}" for a in items] or ['无。'])
    lines += ['', '自动发现的新条目进入待确认，普通版本更新不代表适配；人工审核结论单独保留。']
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
    discovery_changed = any(before.get(key) != after.get(key) for key in ('lastDiscoverySync', 'lastDiscoverySyncUS'))
    if queue.exists() and discovery_changed:
        q = json.loads(queue.read_text())
        report['coverageCN'] = q.get('coverageCN', {})
        report['coverageUS'] = q.get('coverageUS', {})
        report['scanOutcomes'] = q.get('lastScanOutcomes', {})
    data.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n')
    folder = Path('docs/updates'); folder.mkdir(exist_ok=True)
    content = render(report)
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
