(() => {
  'use strict';
  const node = document.getElementById('syncReport');
  const select = document.getElementById('updateRun');
  if (!node || !select) return;
  const status = {unverified: '待确认', apple_featured: '苹果官方介绍', community_verified: '用户实测'};
  const kinds = [['software', '新增软件'], ['game', '新增游戏'], ['unknown', '其他新增']];
  let seed = {}, catalog = {};
  const date = value => {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? '时间未知' : parsed.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai', hour12: false, year: 'numeric', month: '2-digit',
      day: '2-digit', hour: '2-digit', minute: '2-digit'
    });
  };
  function textElement(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
  }
  function appType(app) {
    // Resolve old reports using today's authoritative genre metadata when possible.
    const current = catalog[app.id];
    if (current && window.DuoCatalog) return window.DuoCatalog.type(current, seed);
    return app.appType === 'software' || app.appType === 'game' ? app.appType : 'unknown';
  }
  function storeURL(value) {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && url.hostname === 'apps.apple.com' && !url.username && !url.password ? url.href : '';
    } catch { return ''; }
  }
  function appRow(app, kind) {
    const item = textElement('li', 'update-row', '');
    const main = textElement('div', 'update-row-main', '');
    const url = storeURL(app.appStoreUrl);
    const name = textElement(url ? 'a' : 'span', 'update-app-name', app.name || '未命名 App');
    if (url) {name.href = url; name.target = '_blank'; name.rel = 'noopener noreferrer';}
    main.append(name);
    const version = kind === 'updated' && app.previousVersion
      ? `${app.previousVersion} → ${app.version || '—'}`
      : (kind === 'signals' ? app.evidence?.version : app.version);
    if (version) main.append(textElement('span', 'update-version', version));
    item.append(main);
    if (kind === 'added') item.append(textElement('span', 'update-status', status[app.status] || '状态待核对'));
    if (kind === 'signals' && app.evidence?.excerpt) {
      item.append(textElement('p', 'update-excerpt', app.evidence.excerpt));
    }
    return item;
  }
  function addList(parent, title, items, kind) {
    if (!items.length) return;
    const section = textElement('section', 'update-group', '');
    section.append(textElement('h3', 'update-group-title', `${title} · ${items.length}`));
    const list = textElement('ul', 'update-list', '');
    const initial = 6;
    items.slice(0, initial).forEach(app => list.append(appRow(app, kind)));
    section.append(list);
    if (items.length > initial) {
      const more = textElement('button', 'update-more', `展开其余 ${items.length - initial} 款`);
      more.type = 'button'; more.setAttribute('aria-expanded', 'false');
      more.addEventListener('click', () => {
        const expanded = more.getAttribute('aria-expanded') === 'true';
        if (expanded) {
          while (list.children.length > initial) list.lastElementChild.remove();
        } else items.slice(initial).forEach(app => list.append(appRow(app, kind)));
        more.setAttribute('aria-expanded', String(!expanded));
        more.textContent = expanded ? `展开其余 ${items.length - initial} 款` : '收起';
      });
      section.append(more);
    }
    parent.append(section);
  }
  function render(report) {
    node.replaceChildren();
    const counts = textElement('div', 'update-counts', '');
    [['新增', report.added.length], ['版本更新', report.updated.length], ['适配线索', report.signals.length]].forEach(([label, count]) => {
      const countItem = textElement('span', 'update-count', label + ' ');
      countItem.append(textElement('strong', '', String(count)));
      counts.append(countItem);
    });
    node.append(counts);
    if (!report.added.length) node.append(textElement('p', 'report-empty', '本轮暂无新增应用。'));
    for (const [kind, title] of kinds) addList(node, title, report.added.filter(app => appType(app) === kind), 'added');
    if (report.updated.length || report.signals.length) {
      const details = document.createElement('details'); details.className = 'update-secondary';
      details.append(textElement('summary', '', '其他更新'));
      addList(details, '版本更新', report.updated, 'updated');
      addList(details, '适配线索', report.signals, 'signals');
      node.append(details);
    }
    node.append(textElement('p', 'update-note', '自动发现的新增应用待确认，适配状态以各应用的证据为准。'));
    node.setAttribute('aria-busy', 'false');
  }
  async function read(path) {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) throw new Error(response.status);
    return response.json();
  }
  async function start() {
    try {
      const latest = await read('./updates/latest.json');
      const results = await Promise.allSettled(['./updates/history.json', './data/app-categories-cn.json', './data/apps.json'].map(read));
      const history = results[0].status === 'fulfilled' && Array.isArray(results[0].value) ? results[0].value : [];
      if (results[1].status === 'fulfilled') seed = results[1].value.apps || {};
      if (results[2].status === 'fulfilled') catalog = Object.fromEntries(results[2].value.apps.map(app => [app.id, app]));
      const seen = new Set();
      const reports = [latest, ...history].filter(report => report && Array.isArray(report.added) && Array.isArray(report.updated) && Array.isArray(report.signals) && !seen.has(report.time) && seen.add(report.time));
      if (!reports.length) throw new Error('No valid reports');
      select.replaceChildren();
      reports.forEach((report, index) => {
        const option = document.createElement('option'); option.value = index;
        option.textContent = `${date(report.time)} · 新增 ${report.added.length}`; select.append(option);
      });
      select.disabled = false;
      select.addEventListener('change', () => render(reports[Number(select.value)]));
      render(reports[0]);
    } catch {
      select.replaceChildren(new Option('暂无记录', '')); select.disabled = true;
      node.replaceChildren(textElement('p', 'report-empty', '更新记录暂不可用，请稍后刷新。'));
      node.setAttribute('aria-busy', 'false');
    }
  }
  start();
})();
