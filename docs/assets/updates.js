(() => {
  'use strict';
  const node=document.getElementById('syncReport');
  const select=document.getElementById('updateRun');
  const textbox=document.getElementById('weiboText');
  const status={unverified:'待确认',apple_featured:'苹果官方介绍',community_verified:'用户实测'};
  const kinds=[['software','软件'],['game','游戏'],['unknown','类型待同步']];
  let seed={}, catalog={};
  const date=value=>new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
  const group=items=>kinds.map(([kind,label])=>[kind,label,items.filter(a=>a.appType===kind||((!a.appType||a.appType==='unknown')&&kind==='unknown'))]);
  function paragraph(text, parent=node) {const p=document.createElement('p');p.textContent=text;parent.append(p);}
  function enrich(report) {
    return {...report, added:report.added.map(a=>{
      if(a.appType) return a;
      const app=catalog[a.id] || a;
      return {...a,appType:window.DuoCatalog.type(app,seed)};
    })};
  }
  function render(report) {
    report=enrich(report);node.replaceChildren();
    paragraph(`${date(report.time)}（北京时间） · 新增收录 ${report.added.length} 款 · 版本资料更新 ${report.updated.length} 款 · 适配线索变化 ${report.signals.length} 款`);
    const counts=document.createElement('div');counts.className='update-counts';
    for(const [,label,items] of group(report.added)){const span=document.createElement('span');span.textContent=`新增${label} ${items.length} 款`;counts.append(span);}
    node.append(counts);
    function listSection(title,items,signal=false) {
      const details=document.createElement('details');details.open=title.startsWith('新增');
      const summary=document.createElement('summary');summary.textContent=`${title}（${items.length}）`;details.append(summary);
      const list=document.createElement('ul');
      for(const app of items) {
        const item=document.createElement('li');
        item.textContent=`${app.name} · ${app.previousVersion?app.previousVersion+' → ':''}${app.version||'版本未知'} · ${status[app.status]||'状态待核对'}`;
        if(signal) item.textContent+=` · ${app.evidence?.excerpt||''}`;
        list.append(item);
      }
      if(!items.length) paragraph('本轮无此类更新。',details);
      details.append(list);node.append(details);
    }
    group(report.added).forEach(([,label,items])=>{if(items.length||label!=='类型待同步')listSection('新增'+label,items);});
    listSection('已有 App 版本资料更新',report.updated);
    listSection('适配线索变化',report.signals,true);
    const c=report.coverageCN;
    if(c) paragraph(`国区候选池 ${c.poolSize} 个；计划查询 ${c.lookupScheduled} 个${Number.isInteger(c.lookupReturned)?'，接口返回 '+c.lookupReturned+' 个':''}${Number.isInteger(c.gameFeedsAttempted)?'；游戏子分类榜单成功 '+c.gameFeedsSucceeded+'/'+c.gameFeedsAttempted:''}。候选池不代表全部国区 App。`);
    paragraph('普通版本更新不代表适配。自动发现的新条目进入待确认，人工审核结论单独保留。');
    const names=group(report.added).filter(([, ,items])=>items.length).map(([,label,items])=>`新增${label} ${items.length} 款：${items.map(a=>a.name).join('、')}。`).join('\n');
    textbox.value=report.addedCounts&&report.weiboText ? report.weiboText : `iPhone Duo App 适配目录更新：\n${names||'本轮没有新增收录 App。'}\n自动发现的条目待确认，开发者声明不代表本站实测。\nhttps://vankerwu.github.io/iPhone-Duo-Apps/`;
    document.getElementById('copyStatus').textContent='';
  }
  async function read(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw Error(r.status);return r.json();}
  async function start() {
    try {
      const latest=await read('./updates/latest.json');
      const results=await Promise.allSettled(['./updates/history.json','./data/app-categories-cn.json','./data/apps.json'].map(read));
      const history=results[0].status==='fulfilled'&&Array.isArray(results[0].value)?results[0].value:[];
      if(results[1].status==='fulfilled')seed=results[1].value.apps||{};
      if(results[2].status==='fulfilled')catalog=Object.fromEntries(results[2].value.apps.map(a=>[a.id,a]));
      const seen=new Set();
      const reports=[latest,...history].filter(r=>r&&Array.isArray(r.added)&&Array.isArray(r.updated)&&Array.isArray(r.signals)&&!seen.has(r.time)&&seen.add(r.time));
      reports.forEach((r,i)=>{const option=document.createElement('option');option.value=i;option.textContent=`${date(r.time)} · 新增 ${r.added.length} 款`;select.append(option);});
      select.addEventListener('change',()=>render(reports[Number(select.value)]));render(reports[0]);
    } catch {node.textContent='暂时无法读取更新报告，请稍后刷新或查看历史报告。';}
  }
  document.getElementById('copyWeibo').addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText(textbox.value);document.getElementById('copyStatus').textContent='已复制';}
    catch {textbox.focus();textbox.select();document.getElementById('copyStatus').textContent='请长按或按 Ctrl/Cmd+C 复制选中的文案。';}
  });
  start();
})();
