'use strict';

// Set this to the GitHub repository that will host this NEW WEBSITE.
// Do not point it to the DuoCinema player project unless you want issues there.
const REPOSITORY = 'VankerWu/iPhone-Duo-Apps';
const DATA_URL = './data/apps.json';
const APPLE_LOOKUP = 'https://itunes.apple.com/lookup';
const APP_STORE_CACHE_KEY = 'iphone-duo-appstore-cache-v4';
const STATUS = {
  apple_featured: { label: '苹果官方介绍', hint: '出现在苹果公开介绍 iPhone Duo 应用的资料中。不是本站实测结论。' },
  community_verified: { label: '用户实测', hint: '人工核查真实用户提交的版本、姿态与画面证据。' },
  unverified: { label: '待确认', hint: '收录在观察名单中，目前没有足够证据判断适配情况。' }
};
const $ = id => document.getElementById(id);
const state = { apps: [], query: '', status: 'all', region: 'all', category: 'all', sort: 'recommended', lastSync: null, type: 'all', leadOnly: false };
const categoriesState = {taxonomy:{main:{},games:{}}, seed:{}};
const catalogRules = window.DuoCatalog;
const categoryLabel = app => catalogRules.label(app, categoriesState.seed, categoriesState.taxonomy);

function safe(text) {
  return String(text ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
}
function cleanURL(url) {
  try {
    const parsed = new URL(url);
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : '';
  } catch { return ''; }
}
// An Apple product ID is a stable direct link, unlike a search result page.
function storeURL(app) {
  const numericId = Number(app.itunesId);
  if (!Number.isSafeInteger(numericId) || numericId <= 0) return '';
  const region = app.storefront === 'cn' ? 'cn' : 'us';
  return `https://apps.apple.com/${region}/app/id${numericId}`;
}
function validArtwork(url) {
  if (!url) return '';
  try {
    const link = new URL(url);
    if (link.protocol !== 'https:') return '';
    if (!/^(?:[a-z0-9-]+\.)?mzstatic\.com$/i.test(link.hostname)) return '';
    return link.href;
  } catch { return ''; }
}
// Never invent an App Store icon: show a neutral placeholder until Apple supplies it.
function iconFor(app, large = false) {
  const icon = validArtwork(app.artwork);
  const largeClass = large ? ' app-icon-large' : '';
  return `<span class="app-icon${largeClass}${icon ? ' app-icon-real' : ' app-icon-pending'}">
    <span class="app-icon-empty" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><rect x="6" y="6" width="20" height="20" rx="5" stroke="currentColor" stroke-width="2"/><path d="M11 19l5-9 5 9M12.5 16.6h7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
    ${icon ? `<img src="${safe(icon)}" alt="${safe(app.name)} App Store 图标" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'" />` : ''}
  </span>`;
}
function countByStatus(status) { return state.apps.filter(a => a.status === status).length; }
function updateCounts() {
  $('typeAll').textContent = state.apps.length;
  $('typeSoftware').textContent = state.apps.filter(a=>catalogRules.type(a,categoriesState.seed)==='software').length;
  $('typeGame').textContent = state.apps.filter(a=>catalogRules.type(a,categoriesState.seed)==='game').length;
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
  return state.apps.filter(a => catalogRules.matches(a,state,categoriesState.seed,categoriesState.taxonomy)).sort((a,b) => {
    if (state.sort === 'added') return (b.addedAt || '').localeCompare(a.addedAt || '');
    if (state.sort === 'name') return a.name.localeCompare(b.name,'zh-CN');
    if (state.sort === 'recent') return (b.releaseDate || b.sourceDate || '').localeCompare(a.releaseDate || a.sourceDate || '');
    return 0; // Preserve editorial order in the JSON data.
  });
}
function storeButton(app) {
  const url = storeURL(app);
  if (!url) return '<span class="app-store-pending">商店条目待核实</span>';
  return `<a class="app-store-link" href="${safe(url)}" target="_blank" rel="noopener noreferrer"
      aria-label="前往 ${safe(app.name)} 的 App Store 官方页面" title="打开官方 App Store 页面">App Store ↗</a>`;
}
function renderApps() {
  const visible = getVisibleApps();
  $('resultsText').textContent = `显示 ${visible.length} / ${state.apps.length} 款应用`;
  $('emptyState').hidden = visible.length > 0;
  $('appGrid').innerHTML = visible.map(a => `<article class="app-card">
    <button class="app-card-main" type="button" data-app-id="${safe(a.id)}" aria-label="查看 ${safe(a.name)} 详情">
      <div class="app-card-top">${iconFor(a)}<div class="app-title-wrap">
        <div class="app-title">${safe(a.name)}</div>
        <div class="app-subtitle">${safe(a.developer || a.english)} · ${safe(categoryLabel(a))}</div>
      </div></div>
      ${catalogRules.isLead(a) ? '<span class="discovery-tag">新适配线索</span>' : ''}
      <p class="app-note">${safe(a.note)}</p>
    </button>
    <div class="app-bottom"><span class="status-pill ${safe(a.status)}">${safe((STATUS[a.status] || STATUS.unverified).label)}</span>
      ${storeButton(a)}
    </div>
  </article>`).join('');
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
  const store = storeURL(app);
  const storeControl = store
    ? `<a class="main" target="_blank" rel="noopener noreferrer" href="${safe(store)}">在 App Store 查看 / 下载 ↗</a>`
    : `<span class="detail-store-unmatched">尚未核实官方 App Store 条目</span>`;
  $('dialogBody').innerHTML = `<div class="detail-header">${iconFor(app,true)}<div><h2>${safe(app.name)}</h2><p>${safe(app.developer || app.english)} · ${safe(categoryLabel(app))}</p></div></div>
    <div class="detail-main"><span class="status-pill ${safe(app.status)}">${safe(st.label)}</span><p>${safe(app.note)}</p><p style="font-size:11px">${safe(st.hint)}</p></div>
    <dl><div class="detail-info"><dt>主要地区</dt><dd>${safe(app.region)}</dd></div>
    <div class="detail-info"><dt>App Store 分类</dt><dd>${safe((catalogRules.metadata(app,categoriesState.seed).genres || []).join(' / ') || '分类待同步')}</dd></div>
    <div class="detail-info"><dt>App Store 版本</dt><dd>${safe(app.version || '苹果官方版本信息同步中')}</dd></div>
    <div class="detail-info"><dt>商店来源</dt><dd>${store ? 'Apple App Store 官方应用页面' : '尚未核实'}</dd></div>
    <div class="detail-info"><dt>适配依据</dt><dd>${source ? `<a href="${safe(source)}" target="_blank" rel="noopener noreferrer">${safe(app.sourceLabel || '查看原始资料')} ↗</a>` : '暂无可靠适配证据'}</dd></div>
    <div class="detail-info"><dt>来源日期</dt><dd>${safe(app.sourceDate || '待验证')}</dd></div></dl>
    ${app.duoDiscovery ? `<div class="detail-evidence"><strong>开发者适配声明 · 待核验</strong><p>${safe(app.duoDiscovery.excerpt)}</p><p>证据版本 ${safe(app.duoDiscovery.version)} · ${safe(app.duoDiscovery.date)}；不代表本站实测。</p></div>` : ''}
    <div class="detail-buttons">${storeControl}<a href="${safe(reportURL(app))}" target="_blank" rel="noopener noreferrer">提交实测 / 纠错 ↗</a></div>
    <p class="detail-store-note">应用图标、版本和官方商店页面来自 Apple 的公开资料；这不代表 App 已通过本站折叠屏适配实测。</p>`;
  $('detailDialog').showModal();
}

// Live, ID-based lookup is supplementary to the scheduled GitHub Actions sync.
// It can paint real icons even before the site's JSON is updated on GitHub.
// If Apple's API is temporarily unavailable, already verified direct links still work.
function readStoreCache() {
  try {
    const value = JSON.parse(localStorage.getItem(APP_STORE_CACHE_KEY) || '{}');
    if (!value || Date.now() - value.at > 24 * 60 * 60 * 1000) return {};
    return value.apps || {};
  } catch { return {}; }
}
function writeStoreCache(cache) {
  try { localStorage.setItem(APP_STORE_CACHE_KEY, JSON.stringify({at:Date.now(),apps:cache})); }
  catch { /* Private browsing may disable localStorage. */ }
}
async function lookupIDs(ids, country) {
  const query = new URLSearchParams({id: ids.join(','), country, entity:'software'});
  const response = await fetch(`${APPLE_LOOKUP}?${query}`, {mode:'cors',signal:AbortSignal.timeout(9000)});
  if (!response.ok) throw new Error(`App Store ${response.status}`);
  const body = await response.json();
  return (body.results || []).filter(item =>
    Number.isSafeInteger(item.trackId) && item.kind === 'software' && validArtwork(item.artworkUrl100));
}
async function hydrateStoreIcons() {
  const cache = readStoreCache();
  let changed = false;
  const applyTrack = (app, entry) => {
    if (!entry || Number(entry.trackId) !== Number(app.itunesId)) return;
    const img = validArtwork(entry.artworkUrl512 || entry.artworkUrl100);
    if (img && app.artwork !== img) {app.artwork = img; changed = true;}
    if (entry.artistName && !app.developer) {app.developer = entry.artistName;changed = true;}
    if (entry.version && app.version !== entry.version) {app.version = entry.version;changed = true;}
    cache[String(app.itunesId)] = {artwork:app.artwork,developer:app.developer,version:app.version};
  };
  for (const app of state.apps) {
    const saved = cache[String(app.itunesId)];
    if (saved && !validArtwork(app.artwork)) {
      const url = validArtwork(saved.artwork);
      if (url) {app.artwork=url;changed=true;}
      if (!app.developer && saved.developer) app.developer=saved.developer;
    }
  }
  if (changed) renderApps();
  const groups = {cn:[],us:[]};
  for (const app of state.apps) {
    if (Number.isSafeInteger(Number(app.itunesId)) && !validArtwork(app.artwork)) {
      const key = app.storefront === 'cn' ? 'cn' : 'us';
      groups[key].push(app);
    }
  }
  for (const country of ['cn','us']) {
    for (let offset = 0; offset < groups[country].length; offset += 30) {
      const batch = groups[country].slice(offset, offset+30);
      try {
        const items = await lookupIDs(batch.map(a=>Number(a.itunesId)),country);
        const byID = new Map(items.map(item=>[item.trackId,item]));
        changed = false;
        for (const app of batch) applyTrack(app,byID.get(Number(app.itunesId)));
        if (changed) {writeStoreCache(cache);renderApps();}
      } catch (err) {console.info('App Store 图标暂无法即时获取，等待 GitHub Actions 同步：',err.message);}
    }
  }
  if ($('detailDialog').open) {
    const current = state.apps.find(a=>a.name===$('dialogBody').querySelector('h2')?.textContent);
    const oldIcon = $('dialogBody').querySelector('.detail-header .app-icon');
    if (current && oldIcon) oldIcon.outerHTML = iconFor(current,true);
  }
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

async function loadCategories() {
  const paths=['./data/app-store-genres.json','./data/app-categories-cn.json'];
  const results=await Promise.allSettled(paths.map(async path=>{const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error(r.status);return r.json();}));
  if(results[0].status==='fulfilled') categoriesState.taxonomy=results[0].value;
  if(results[1].status==='fulfilled') categoriesState.seed=results[1].value.apps || {};
}
function populateCategories() {
  const select=$('categorySelect');select.replaceChildren(new Option('全部分类','all'));
  const taxonomy=categoriesState.taxonomy;
  const apps=state.apps.filter(a=>state.type==='all'||catalogRules.type(a,categoriesState.seed)===state.type);
  const known=new Set(apps.flatMap(a=>catalogRules.ids(a,categoriesState.seed)));
  const group=(title,entries)=>{
    const node=document.createElement('optgroup');node.label=title;
    entries.filter(([id])=>known.has(id)).sort((a,b)=>a[1].name.localeCompare(b[1].name,'zh-CN')).forEach(([id,genre])=>node.append(new Option(genre.name,id)));
    if(node.children.length)select.append(node);
  };
  if(state.type!=='game') group('软件主分类与其他分类',Object.entries(taxonomy.main).filter(([id])=>state.type==='all'||id!=='6014'));
  if(state.type!=='software') group('游戏子分类',Object.entries(taxonomy.games));
  if(apps.some(a=>catalogRules.type(a,categoriesState.seed)==='game'&&!catalogRules.ids(a,categoriesState.seed).some(id=>taxonomy.games[id])))select.append(new Option('游戏 · 子分类待同步','game-unspecified'));
  if(apps.some(a=>!catalogRules.metadata(a,categoriesState.seed).primaryGenreId))select.append(new Option('分类待同步','unclassified'));
  const unknown=state.apps.filter(a=>catalogRules.type(a,categoriesState.seed)==='unknown').length;
  $('categoryHelp').textContent='按国区 App Store 分类整理，主分类展示，筛选包含其他返回分类。'+(unknown?`另有 ${unknown} 款分类待同步，可在“全部”查看。`:'');
  $('categoryLabel').textContent=state.type==='game'?'游戏子分类':'App Store 分类';
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
  document.querySelectorAll('.type-tab').forEach(button=>button.addEventListener('click',()=>{
    state.type=button.dataset.type;state.category='all';
    document.querySelectorAll('.type-tab').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});
    populateCategories();renderApps();
  }));
  $('leadOnly').addEventListener('change',e=>{state.leadOnly=e.target.checked;renderApps();});
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
  await loadCategories();
  populateCategories();
  updateCounts(); renderApps();
  // Non-blocking icon retrieval. Direct App Store IDs are available immediately.
  hydrateStoreIcons().catch(error => console.info(error));
}
document.addEventListener('DOMContentLoaded',start);
