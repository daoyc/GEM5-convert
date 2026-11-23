const profileRegistry=new Map();
let profile=null, corePath='system.cpu', profileSerial=0, viewCache=new Map();
let configContext;
const shortValue=r=>ProfileView.format(r);
function graphFor(base){
  if(viewCache.has(base))return viewCache.get(base);
  const rows=configContext.rows(base.id);
  const g={...base,geometry:null,rows, imported:null};
  const subset=id=>rows.filter(r=>r.node===id);
  
  function moduleReason(id){
    if(!profile)return '';
    const f=profile.objects;
    const owner={bpu:'branchPred',ftq:'branchPred',mmu:'mmu',icache:'icache',dcache:'dcache',llc:'l3',fabric:'membus',mem:'mem_ctrls',l2:'slice'}[id];
    if(owner&&!configContext.owners(owner).some(p=>f.has(p)))return '实例未提供';
    if(['bpu','ftq'].includes(id)&&f.get(corePath+'.branchPred')?.type!=='DecoupledBPUWithBTB')return '预测器实现不同';
    if(id==='mem'&&!configContext.owners(owner).every(p=>String(f.get(p)?.type).toLowerCase()==='dramsim3'))return '控制器实现不同';
    if(id==='l2'&&!configContext.owners('wrapper').length)return '经典 L2 · 无切片流水线';
    return '';
  }
  const unavailable=new Map();
  g.nodes=base.nodes.map(n=>{
    const own=subset(n.id), vals=n.target?configContext.rows(n.target):own;
    let sub=n.sub, detail=n.detail, reason=moduleReason(n.target||base.id);
    if(vals.length){
      const r=vals[0], text=shortValue(r);
      sub=r.key==='enabled'?r.label+' · '+text:r.label+' '+text;
      if(own.length && profile)detail=own.slice(0,2).map(x=>x.label+' '+shortValue(x)).join(' · ');
    }
    if(base.id==='bpu'&&own.length){
      const enabled=own.filter(x=>shortValue(x)==='启用');
      if(n.id==='components'){
        sub='组合预测 · '+enabled.length+'/'+own.length+' 启用';
        detail=own.map(x=>x.label+' '+shortValue(x)).join(' · ');
      }else if(!enabled.length)reason=own[0].value==null?'开关未提供':'已关闭';
    }
    if(base.id==='ifu'&&n.id==='pre'&&profile&&shortValue(own[0])!=='启用')reason=own[0].value==null?'开关未提供':'检查已关闭';
    if(profile && base.id==='dispatch' && n.id==='admit' && shortValue(own[0])!=='关闭')reason='直接分派路径未确认';
    if(profile && base.id==='mmu' && own.length && !configContext.owners(own[0].owner).some(p=>profile.objects.has(p)))reason='实例未提供';
    if(base.id==='bpu' && n.id==='components' && own.every(r=>shortValue(r)!=='启用'))reason='无已确认的组合预测器';
    if(profile && detail===n.detail && /默认|配置|[0-9]+ 项/.test(detail))detail='源码默认结构对照 · '+detail;
    if(reason)detail=reason+' · '+detail;
    if(reason)unavailable.set(n.id,reason);
    return {...n,sub:reason||sub,detail,reason};
  });
  g.streams=base.streams.filter(s=>!s.steps.some(t=>unavailable.has(t.a)||unavailable.has(t.b)));
  g.blocked=unavailable;
  g.excluded=[...(base.excludedSources||[]),...base.streams.filter(s=>!g.streams.includes(s)).map(s=>s.name)];
  if(profile){
    g.streams=g.streams.map(s=>({...s,steps:s.steps.map(t=>{
      if(base.id==='dispatch'&&t.a==='rename'&&t.b==='admit')return {...t,text:'独立分派级关闭，直接接收 Rename 输出。'};
      if(base.id==='decode'&&t.a==='ifu'&&t.b==='input')return {...t,text:'取出当前线程的取指输出。'};
      return t;
    })}));
  }
  viewCache.set(base,g);return g;
}
function drawParams(){
  const panel=$('params'), list=$('paramRows');
  panel.hidden=graph.id==='overview';list.replaceChildren();
  if(panel.hidden)return;
  $('paramOrigin').textContent=profile?(profile.sample?'测试输入':'运行配置输入'):'源码默认';
  for(const r of graph.rows){
    const line=document.createElement('div'), label=document.createElement('span'), val=document.createElement('strong'), ref=document.createElement('small');
    label.textContent=r.label;val.textContent=shortValue(r);
    ref.append(r.scope+' · ');
    if(profile)ref.append(r.origin);else if(r.path)ref.append(source(r.path,r.key+' · '+r.path.split('/').at(-1)));else ref.append('来源未定位');
    line.append(label,val,ref);list.append(line);
  }
}
function switchProfile(key,core){
  const keep=selected, name=profileRegistry.get(key);
  selectionToken++;
  profile=name||null;
  corePath=profile?.cores.includes(core)?core:profile?.cores[0]||'system.cpu';
  configContext=ProfileView.context(profile,corePath);
  $('core').replaceChildren(...(profile?.cores||[corePath]).map(p=>new Option(p,p)));$('core').value=corePath;
  $('profile').value=key;$('core').disabled=!profile||profile.cores.length<2;
  stop();sessions.clear();viewCache.clear();graph=null;openGraph(keep);
}
async function decodeConfig(file){
  const text=(await file.text()).replace(/^\uFEFF/,'');
  return ProfileView.load({nodes:decodeInstances(file.name,text)});
}
async function registerFiles(files){
  for(const f of files){
    try{
      const p=await decodeConfig(f), id='file-'+(++profileSerial);
      profileRegistry.set(id,p);$('profile').add(new Option(f.name+' · #'+profileSerial,id));switchProfile(id,corePath);
      $('configMsg').textContent='';
    }catch(e){$('configMsg').textContent=f.name+' · '+e.message;break}
  }
}
$('profileFiles').onchange=async e=>{const input=e.target;await registerFiles([...input.files]);input.value=''};
$('core').onchange=e=>switchProfile($('profile').value,e.target.value);
let selectionToken=0;
$('profile').onchange=async e=>{
  const key=e.target.value, token=++selectionToken;
  try{
    if(key.startsWith('sample')&&!profileRegistry.has(key)){
      const file=key==='sampleA'?'baseline.ini':'variant.json';
      let text=sampleConfigs[key];
      if(text===undefined){
        const response=await fetch('../examples/'+file);
        if(!response.ok)throw Error('无法读取测试配置 '+file);
        text=await response.text();
      }
      const p=ProfileView.load({nodes:decodeInstances(file,text)});
      p.sample=true;profileRegistry.set(key,p);
    }
    if(token===selectionToken){switchProfile(key,corePath);$('configMsg').textContent=''}
  }catch(err){if(token===selectionToken){$('profile').value=[...profileRegistry].find(([,p])=>p===profile)?.[0]||'default';$('configMsg').textContent=err.message}}
};
