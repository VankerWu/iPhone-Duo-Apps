'use strict';

// Set this to the GitHub repository that will host this NEW WEBSITE.
// Do not point it to the DuoCinema player project unless you want issues there.
const REPOSITORY = 'VankerWu/iPhone-Duo-Apps';
const DATA_URL = './data/apps.json';
const STATUS = {
  apple_featured: { label: '苹果官方介绍', hint: '出现在苹果公开介绍 iPhone Duo 应用的资料中。不是本站实测结论。' },
  community_verified: { label: '用户实测', hint: '人工核查真实用户提交的版本、姿态与画面证据。' },
  unverified: { label: '待确认', hint: '收录在观察名单中，目前没有足够证据判断适配情况。' }
};
const gradients = [
  'linear-gradient(135deg,#4e6fff,#7fb4e9)',
  'linear-gradient(135deg,#4fbaa3,#8ad8dc)',
  'linear-gradient(135deg,#7173d5,#b19de6)',
  'linear-gradient(135deg,#dd8a6b,#f2be8d)',
  'linear-gradient(135deg,#3963a6,#4bc2ce)',
  'linear-gradient(135deg,#71809c,#a9b8ce)'
];
const $ = id => document.getElementById(id);
const state = { apps: [], query: '', status: 'all', region: 'all', category: 'all', sort: 'recommended', lastSync: null };

function safe(text) {
  return String(text ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
}
function cleanURL(url) {
  try {
    const parsed = new URL(url);
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : '';
  } catch { return ''; }
}
function iconFor(app, large = false) {
  const short = app.name.replace(/\s/g,'').slice(0,2);
  const hash = Array.from(app.id).reduce((total, c) => total + c.charCodeAt(0), 0);
  const css = gradients[hash % gradients.length];
  const img = app.artwork && cleanURL(app.artwork) && /^https:\/\/[^/]*mzstatic\.com\//i.test(app.artwork);
  return `<span class="app-icon" style="background:${css};${large ? 'width:64px;height:64px;font-size:22px;border-radius:17px;' : ''}"><span>${safe(short)}</span>${img ? `<img src="${safe(cleanURL(app.artwork))}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'" />` : ''}</span>`;
}
function countByStatus(status) { return state.apps.filter(a => a.status === status).length; }
function updateCounts() {
  $('statTotal').textContent = state.apps.length;
  $('statOfficial').textContent = countByStatus('apple_featured');
  $('statVerified').textContent = countByStatus('community_verified');
  $('statWaiting').textContent = countByStatus('unverified');
  $('countAll').textContent = state.apps.length;
  $('countOfficial').textContent = countByStatus('apple_featured');
  $('countVerified').textContent = countByStatus('community_verified');
  $('countWaiting').textContent = countByStatus('unverified');
  $('metaSync').textContent = state.lastSync ? `App Store 元数据更新 ${state.lastSync.slice(0,10)}` : '首批证据整理：2026.10.22';
}
function getVisibleApps() {
  const needle = state.query.trim().toLocaleLowerCase('zh-CN');
  return state.apps.filter(a => {
    if (state.status !== 'all' && a.status !== state.status) return false;
    if (state.category !== 'all' && a.category !== state.category) return false;
    if (state.region !== 'all' && a.region !== state.region && a.region !== '全球') return false;
    if (!needle) return true;
    return [a.name,a.english,a.category,a.developer,a.note].join(' ').toLocaleLowerCase('zh-CN').includes(needle);
  }).sort((a,b) => {
    if (state.sort === 'name') return a.name.localeCompare(b.name,'zh-CN');
    if (state.sort === 'recent') return (b.releaseDate || b.sourceDate || '').localeCompare(a.releaseDate || a.sourceDate || '');
    return 0; // Preserve editorial order in the JSON data.
  });
}
function renderApps() {
  const visible = getVisibleApps();
  $('resultsText').textContent = `显示 ${visible.length} / ${state.apps.length} 款应用`;
  $('emptyState').hidden = visible.length > 0;
  $('appGrid').innerHTML = visible.map(a => `<button class="app-card" type="button" data-app-id="${safe(a.id)}" aria-label="查看 ${safe(a.name)} 详情">
    <div class="app-card-top">${iconFor(a)}<div class="app-title-wrap"><div class="app-title">${safe(a.name)}</div><div class="app-subtitle">${safe(a.developer || a.english)} · ${safe(a.category)}</div></div></div>
    <p class="app-note">${safe(a.note)}</p>
    <div class="app-bottom"><span class="status-pill ${safe(a.status)}">${safe((STATUS[a.status] || STATUS.unverified).label)}</span><span class="app-arrow">↗</span></div></button>`).join('');
}
function reportURL(app) {
  const title = app ? `反馈：${app.name} 在 iPhone Duo 的显示情况` : '提交一款 iPhone Duo 适配应用';
  const body = `## 应用名称\n${app ? app.name : '请填写'}\n\n## App Store 链接\n\n\n## 应用版本\n\n\n## 地区/系统版本\n\n\n## Duo 姿态\n（外屏 / 内屏展开 / 半折叠 / 方向）\n\n## 观察结果\n（例如完整布局 / 拉伸 / 黑边 / 无法使用）\n\n## 图片或证据链接\n\n\n## 补充说明\n\n`;
  return `https://github.com/${REPOSITORY}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}
function showDetails(app) {
  if (!app) return;
  const st = STATUS[app.status] || STATUS.unverified;
  const source = cleanURL(app.sourceUrl);
  const store = cleanURL(app.appStoreUrl);
  $('dialogBody').innerHTML = `<div class="detail-header">${iconFor(app,true)}<div><h2>${safe(app.name)}</h2><p>${safe(app.developer || app.english)} · ${safe(app.category)}</p></div></div>
    <div class="detail-main"><span class="status-pill ${safe(app.status)}">${safe(st.label)}</span><p>${safe(app.note)}</p><p style="font-size:11px">${safe(st.hint)}</p></div>
    <dl><div class="detail-info"><dt>主要地区</dt><dd>${safe(app.region)}</dd></div>
    <div class="detail-info"><dt>版本信息</dt><dd>${safe(app.version || '尚未同步 App Store 元数据')}</dd></div>
    <div class="detail-info"><dt>公开依据</dt><dd>${source ? `<a href="${safe(source)}" target="_blank" rel="noopener noreferrer">${safe(app.sourceLabel || '查看原始资料')} ↗</a>` : '暂无可靠适配证据'}</dd></div>
    <div class="detail-info"><dt>来源日期</dt><dd>${safe(app.sourceDate || '待验证')}</dd></div></dl>
    <div class="detail-buttons">${store ? `<a class="main" target="_blank" rel="noopener noreferrer" href="${safe(store)}">App Store ↗</a>` : ''}<a href="${safe(reportURL(app))}" target="_blank" rel="noopener noreferrer">提交实测 / 纠错 ↗</a></div>`;
  $('detailDialog').showModal();
}
function setupTheme() {
  const current = localStorage.getItem('iphone-duo-app-theme');
  const dark = current ? current === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  $('themeButton').addEventListener('click', () => {
    const newMode = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = newMode;
    localStorage.setItem('iphone-duo-app-theme',newMode);
  });
}

function setupDonationQRs() {
  document.querySelectorAll('.support-card').forEach(card => {
    const img = card.querySelector('.support-qr-image');
    if (!img) return;
    const reflect = () => card.classList.toggle('has-qr', Boolean(img.complete && img.naturalWidth > 0));
    img.addEventListener('load', reflect);
    img.addEventListener('error', reflect);
    reflect();
  });
}

async function start() {
  setupDonationQRs();
  setupTheme();
  $('repoLink').href = `https://github.com/${REPOSITORY}`;
  $('footerRepo').href = `https://github.com/${REPOSITORY}`;
  $('year').textContent = String(new Date().getFullYear());
  const openReport = () => window.open(reportURL(null),'_blank','noopener,noreferrer');
  for (const id of ['submitHero','submitFooter','submitEmpty','submitCta']) $(id).addEventListener('click',openReport);
  $('searchInput').addEventListener('input', e => { state.query = e.target.value; renderApps(); });
  $('categorySelect').addEventListener('change', e => { state.category = e.target.value; renderApps(); });
  $('regionSelect').addEventListener('change', e => { state.region = e.target.value; renderApps(); });
  $('sortSelect').addEventListener('change', e => { state.sort = e.target.value; renderApps(); });
  document.querySelectorAll('.status-tab').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.status-tab').forEach(b => b.classList.remove('active'));
    button.classList.add('active');
    state.status = button.dataset.status;
    renderApps();
  }));
  $('appGrid').addEventListener('click', e => {
    const item = e.target.closest('[data-app-id]');
    if (item) showDetails(state.apps.find(a => a.id === item.dataset.appId));
  });
  $('dialogClose').addEventListener('click',() => $('detailDialog').close());
  $('detailDialog').addEventListener('click',event => {if(event.target === $('detailDialog')) $('detailDialog').close();});
  document.addEventListener('keydown',e => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && !($('detailDialog').open)) {
      e.preventDefault(); $('searchInput').focus();
    }
  });
  let result;
  try {
    const response = await fetch(DATA_URL,{cache:'no-cache'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    result = await response.json();
  } catch (err) {
    // Offline preview: allow Finder → double-click index.html.
    // Live GitHub Pages deployment still reads docs/data/apps.json.
    console.info('Using offline embedded sample data:',err.message);
    try { result = JSON.parse($('embeddedData').textContent); }
    catch (parseError) { console.error(parseError); }
  }
  if (!result || !Array.isArray(result.apps)) {
    $('appGrid').innerHTML = '<div class="empty-state" style="grid-column:1 / -1;display:block"><h3>无法读取应用目录</h3><p>请检查 data/apps.json 或重新下载完整文件包。</p></div>';
    $('resultsText').textContent = '数据暂时不可用';
    return;
  }
  state.apps = result.apps.filter(x => x.name && STATUS[x.status]);
  state.lastSync = result.lastMetadataSync;
  const categories = [...new Set(state.apps.map(a => a.category))].sort((a,b) => a.localeCompare(b,'zh-CN'));
  $('categorySelect').insertAdjacentHTML('beforeend',categories.map(c => `<option value="${safe(c)}">${safe(c)}</option>`).join(''));
  updateCounts(); renderApps();
}
document.addEventListener('DOMContentLoaded',start);
