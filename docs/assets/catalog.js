/* Pure catalog rules shared by filters and tests. No compatibility inference. */
(function(root) {
  'use strict';
  function metadata(app, seed = {}) {
    const value = app.storeCategory || app.storeCategories?.cn || app.storeCategories?.us || seed[String(app.itunesId)];
    return value && ['cn','us'].includes(value.storefront) ? value : {};
  }
  function storefronts(app) {
    const found = Object.keys(app.storeListings || {}).filter(region=>['cn','us'].includes(region));
    const primary = ['cn','us'].includes(app.storefront) ? app.storefront : ({'中国大陆':'cn','美国':'us'}[app.region]);
    if (primary && !found.includes(primary)) found.push(primary);
    return found.sort();
  }
  function type(app, seed) {
    const value=metadata(app, seed).appType;
    return ['software','game'].includes(value) ? value : 'unknown';
  }
  function ids(app, seed) { return (metadata(app, seed).genreIds || []).map(String); }
  function label(app, seed, taxonomy) {
    const meta=metadata(app, seed);
    if (!meta.primaryGenreId) return '分类待同步';
    if (meta.appType==='game') {
      const sub=ids(app, seed).filter(id=>taxonomy.games[id]).map(id=>taxonomy.games[id].name);
      return sub.length ? `游戏 · ${sub.join(' / ')}` : '游戏';
    }
    return meta.primaryGenreName || '分类待同步';
  }
  function isLead(app) { return Boolean(app.duoDiscovery) || app.category==='新适配线索'; }
  function matches(app, state, seed = {}, taxonomy = {main:{},games:{}}) {
    const appType=type(app, seed), genreIds=ids(app, seed);
    if (state.type!=='all' && appType!==state.type) return false;
    if (state.status!=='all' && app.status!==state.status) return false;
    const selectedStore = {'中国大陆':'cn','美国':'us'}[state.region];
    if (state.region!=='all' && app.region!==state.region && app.region!=='全球' &&
        !(selectedStore && storefronts(app).includes(selectedStore))) return false;
    if (state.leadOnly && !isLead(app)) return false;
    if (state.category==='unclassified' && metadata(app, seed).primaryGenreId) return false;
    if (state.category==='game-unspecified' && (appType!=='game'||genreIds.some(id=>taxonomy.games[id]))) return false;
    if (!['all','unclassified','game-unspecified'].includes(state.category) && !genreIds.includes(String(state.category))) return false;
    const needle=state.query.trim().toLocaleLowerCase('zh-CN');
    return !needle || [app.name,app.english,app.developer,app.note,label(app,seed,taxonomy),
      ...(metadata(app,seed).genres||[]),isLead(app)?'新适配线索':''].join(' ').toLocaleLowerCase('zh-CN').includes(needle);
  }
  const api={metadata,storefronts,type,ids,label,isLead,matches};
  if (typeof module==='object'&&module.exports) module.exports=api;
  else root.DuoCatalog=api;
})(typeof globalThis!=='undefined'?globalThis:this);
