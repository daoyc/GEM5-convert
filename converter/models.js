const $ = id => document.getElementById(id);
const registry = new Map();
const configurations = new Map();
const configSelection = new Map();
let model, objects, relations, view, scope, focus, page=0, zoom=1, scene, position=-1, timer;
const replayMemory=new Map();
const importedScenes=new Map();
let choices=[], edgeIndex=new Map(), replayListScene;
function stop(){clearInterval(timer);timer=null;$('play').textContent='▶ 播放'}
function button(el,action){el.setAttribute('role','button');el.setAttribute('tabindex','0');el.onclick=action;el.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();action()}}}
function svg(tag,attrs,parent,text){
  const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);
  if(text!==undefined)el.textContent=text;
  parent.append(el);return el;
}
function showInfo(title, fields){
  const root=$('props'), heading=document.createElement('b');
  heading.textContent=title;root.replaceChildren(heading);
  for(const [label,value] of Object.entries(fields)){
    if(value==null||Array.isArray(value)&&!value.length)continue;
    if(typeof value==='string'){
      const p=document.createElement('p');
      p.textContent=label==='组件作用'?value:label+' · '+value;root.append(p);continue;
    }
    const details=document.createElement('details'),summary=document.createElement('summary'),body=document.createElement('pre');
    summary.textContent=label;
    if(value.file&&value.line){
      const key=value.file+':'+value.line;
      summary.textContent=key;summary.title=label;
      body.textContent=model.excerpts?.[key]||value.text||key;
    }else{
      body.textContent=JSON.stringify(value,null,2);
    }
    details.append(summary,body);root.append(details);
  }
}
function legacy(raw){
  return {...raw, instances:[],connections:[],edges:raw.edges.map(([a,b,label],i)=>({a,b,label,id:'legacy-'+i,kind:label.includes(' → ')?'port':label==='继承'?'inheritance':'reference'}))};
}
function register(key,raw){
  if(!['core-atlas/1','core-atlas/2'].includes(raw?.format)||!raw.nodes?.length||!Array.isArray(raw.edges))throw Error('不支持的模型文件');
  const m=raw.format==='core-atlas/1'?legacy(raw):raw;
  const ids=new Set(m.nodes.map(n=>n.id));
  if(!Array.isArray(m.instances)||!Array.isArray(m.connections)||typeof m.name!=='string'||!m.name.trim()||
     m.view&&(!Array.isArray(m.view.modules)||!Array.isArray(m.view.edges)||(m.view.demo!==undefined&&!Array.isArray(m.view.demo))))throw Error('模型缺少必要字段');
  if(ids.size!==m.nodes.length||m.nodes.some(n=>!n.id||!n.name||!n.fields)||m.edges.some(e=>!ids.has(e.a)||!ids.has(e.b)))throw Error('模型对象或关系无效');
  const base={...m,instances:[],connections:[],config:null,scope:null};
  const versions=new Map([['source',base]]);
  if(m.config)versions.set('included',m);
  configurations.set(key,versions);
  configSelection.set(key,m.config?'included':'source');
  registry.set(key,m);$('model').replaceChildren(...Array.from(registry,([id,v])=>new Option(v.name,id)));$('model').value=key;activate();
}
function showArchitecture(){
  const dialog=$('architecturePage'), frame=dialog.querySelector('iframe');
  delete dialog.dataset.ready;
  frame.src='xs_view/index.html';
  dialog.showModal();
}
function closeArchitecture(){
  const dialog=$('architecturePage');
  if(dialog.open)dialog.close();
}
$('architecturePage').onclose=()=>{
  $('architecturePage').querySelector('iframe').removeAttribute('src');
  openView('source');
};
$('closeArchitecture').onclick=closeArchitecture;
window.addEventListener('message', event=>{
  const dialog=$('architecturePage'), frame=dialog.querySelector('iframe');
  if(!dialog.open || event.source!==frame.contentWindow || event.origin!==location.origin)return;
  if(event.data?.type==='core-atlas:ready'){
    dialog.dataset.ready='true';
    frame.contentWindow.postMessage({type:'core-atlas:model',model},location.origin==='null'?'*':location.origin);
  }else if(event.data?.type==='core-atlas:inspect')closeArchitecture();
});
function activate(keepView){
  stop();replayMemory.clear();importedScenes.clear();view=null;scene=null;
  const key=$('model').value,versions=configurations.get(key),version=configSelection.get(key);
  model=versions.get(version);
  $('configuration').replaceChildren(...Array.from(versions,([k,v])=>new Option(v.config||'源码默认',k)));
  $('configuration').value=version;$('configuration').hidden=versions.size<2;objects=new Map([...model.nodes,...model.instances].map(n=>[n.id,n]));
  relations=[...model.edges,...model.connections];scope=model.scope||'';
  $('scope').replaceChildren(new Option('全部实例',''),...model.instances.filter(n=>/CPU|System/i.test(n.fields.type)||/(^|\.)(cpu\d*|system)$/.test(n.id)).map(n=>new Option(n.id,n.id)));
  if(scope&&!Array.from($('scope').options).some(o=>o.value===scope))$('scope').add(new Option(scope,scope));
  $('scope').value=scope;$('scope').hidden=!model.instances.length;$('config').disabled=model.format!=='core-atlas/2';
  focus=model.nodes.find(n=>n.name==='RiscvO3CPU')?.id||model.nodes[0].id;
  $('search').value='';search();$('view').replaceChildren(...[
    ...(model.view?[new Option('整核总览',model.view.id),...model.view.modules.map(m=>new Option(m.name,m.id))]:[]),
    new Option('源码与实例检查','source')]);openView([...$('view').options].some(o=>o.value===keepView)?keepView:(model.view?.id||'source'));
  if(model.architecture?.id==='xs-dev.kmhv3')showArchitecture();
}
function search(){
  const term=$('search').value.toLowerCase();
  $('object').replaceChildren(new Option('选择对象',''),...Array.from(objects.values()).filter(n=>(n.kind!=='instance'||scoped(n.id))&&(n.id+' '+n.name).toLowerCase().includes(term)).map(n=>new Option(n.name,n.id)));
}
// A config export can disagree with the statically selected implementation.
// Only exclude logical routes when an instance provides contradictory evidence.
function replayEligibility(target){
  const all=availableEdges(target).filter(e=>!e.requiresRuntime||featureState(e)==='启用');
  if(!model.config || !model.view || target==='source')return {edges:all,notes:[]};
  const graph=model.view.modules.find(m=>m.id===target);
  const expected=model.view.modules.find(m=>m.id==='bpu')?.parameters?.['预测器']?.value;
  const controllers=model.view.modules.find(m=>m.id==='mem');
  const checks=[];
  if(expected)checks.push({modules:['bpu','ftq'],instance:/\.branchPred$/,expected});
  if(controllers?.parts.some(p=>p.evidence?.file==='src/mem/dramsim3.cc')){
    checks.push({modules:['mem'],instance:/\.mem_ctrls\d*$/,expected:'DRAMsim3'});
  }
  const excluded=new Set(),notes=[];
  for(const rule of checks){
    const conflicts=model.instances.filter(n=>scoped(n.id)&&rule.instance.test(n.id)&&n.fields.type&&
      String(n.fields.type).toLowerCase()!==String(rule.expected).toLowerCase());
    if(!conflicts.length)continue;
    const depends=id=>rule.modules.includes(graph?.id)||rule.modules.includes(id)||
      rule.modules.includes(graph?.parts.find(part=>part.id===id)?.target);
    const affected=all.filter(e=>e.kind!=='port'&&(depends(e.a)||depends(e.b)));
    if(!affected.length)continue;
    for(const e of affected)excluded.add(e.id);
    notes.push('当前源码图采用 '+rule.expected+'，运行实例 '+conflicts.map(n=>n.id+' = '+n.fields.type).join('、')+'；已停用相关源码演示');
  }
  return {edges:all.filter(e=>!excluded.has(e.id)),notes};
}
function openView(id){
  stop();
  if(view && scene)replayMemory.set(view,{id:scene.id,position});
  view=id;page=0;zoom=1;$('view').value=id;
  drawCoverage();
  const {edges,notes}=replayEligibility(id);
  edgeIndex=new Map(edges.map(e=>[e.id,e]));
  const graph=model.view && (id===model.view.id?model.view:model.view.modules.find(m=>m.id===id));
  choices=[];
  if(graph){
    for(const template of graph.scenarios||[]){
      const valid=template.steps?.length && template.steps.every(s=>{
        const edge=edgeIndex.get(s.edgeId);
        return edge && edge.a===s.a && edge.b===s.b;
      });
      if(valid&&(!template.requiresRuntime||featureState(template)==='启用'))choices.push({...template,origin:'源码演示'});
    }
    if(!choices.length && graph===model.view && graph.demo?.length===5 && graph.demo.every(key=>edgeIndex.has(key))){
      const steps=graph.demo.map(key=>demoStep(edgeIndex.get(key)));
      choices.push({id:'legacy-demo',name:'取指与地址翻译',origin:'演示回放',steps});
    }
    if(!choices.length){
      for(const e of edges.filter(e=>e.kind==='logical-flow'||e.kind==='port')){
        choices.push({id:'single:'+e.id,name:e.label,origin:'单链路演示',steps:[demoStep(e)]});
      }
    }
  }
  const imported=importedScenes.get(id);
  if(imported)choices.push(imported);
  const saved=replayMemory.get(id);
  const ix=choices.findIndex(s=>s.id===saved?.id);
  $('scenario').replaceChildren(...choices.map((s,i)=>new Option(s.name,i)));
  $('message').textContent=[...notes,...(model.view?.warnings||[]),...(model.warnings||[])].filter(Boolean).join(' · ');
  $('home').disabled=!model.view&&!model.architecture;
  selectScene(ix<0?0:ix,ix<0?0:saved.position);
}
function demoStep(e){
  return {edgeId:e.id,a:e.a,b:e.b,type:e.kind==='port'?'端口':'传递',text:e.label};
}
function selectScene(i,offset=0){
  stop();scene=choices[i];
  $('scenario').disabled=$('step').disabled=$('play').disabled=!scene;
  $('scene').textContent=scene?.origin||'';
  if(scene){
    $('scenario').value=String(i);
    advance(Math.min(offset,scene.steps.length-1));
  }else{
    position=-1;
    $('event').textContent=view==='source'?'可导入与实例端口对应的 trace':'当前模型中没有可绑定的有向事件';
    draw();
  }
}
function eventEndpoints(step){
  const edge=edgeIndex.get(step.edgeId);
  const module=model.view?.modules.find(m=>m.id===view);
  const name=id=>module?.parts.find(n=>n.id===id)?.name || model.view?.modules.find(n=>n.id===id)?.name || id;
  const pair=edge?.moduleA?[edge.moduleA,edge.moduleB]:[step.a,step.b];
  if(edge?.moduleA && step.reverse)pair.reverse();
  return pair.map(name).join(' → ');
}
function replayList(){
  const list=$('sequence');
  if(scene!==replayListScene){
    list.replaceChildren();
    for(const [i,step] of (scene?.steps||[]).entries()){
      const item=document.createElement('li'),btn=document.createElement('button');
      for(const [part,text] of [['num',String(i+1).padStart(2,'0')],['type',step.type],['route',eventEndpoints(step)],['detail',step.text]]){
        const span=document.createElement('span');span.className='step-'+part;span.textContent=text;btn.append(span);
      }
      btn.onclick=()=>{stop();advance(i)};
      item.append(btn);list.append(item);
    }
    replayListScene=scene;
  }
  const old=list.querySelector('.active');
  if(old){old.classList.remove('active');old.removeAttribute('aria-current')}
  const current=list.children[position]?.firstChild;
  if(current){
    current.classList.add('active');current.setAttribute('aria-current','step');
    const row=current.getBoundingClientRect(),box=list.getBoundingClientRect();
    if(row.top<box.top)list.scrollTop+=row.top-box.top;
    else if(row.bottom>box.bottom)list.scrollTop+=row.bottom-box.bottom;
  }
}
function inspectObject(n){
  const params={};
  for(const uid of [...(n.lineage||[])].reverse())Object.assign(params,objects.get(uid)?.parameters);
  showInfo(n.name,{'源码依据':n.evidence||n.source||n.id,'声明默认与继承参数':params,'配置覆盖证据':(model.view?.overrides||[]).filter(o=>Object.keys(params).includes(o.target.split('.').pop())),'字段':n.fields,...(n.declaration?{'声明位置':objects.get(n.declaration)?.evidence}:{})});
}
function importFile(id,handler){
  $(id).onchange=async e=>{const file=e.target.files[0],before=model,sceneView=view;if(!file)return;
    try{const raw=JSON.parse(await file.text());if(before===model&&sceneView===view)await handler(raw,file.name)}
    catch(error){$('message').textContent=error.message}finally{e.target.value=''}};
}
function bindTrace(raw, candidates,viewId){
  if(!raw?.name||!Array.isArray(raw.steps)||!raw.steps.length)throw Error('trace 缺少名称或步骤');
  if(raw.viewId!==undefined&&raw.viewId!==viewId || raw.graph!==undefined&&![viewId,model.name].includes(raw.graph))throw Error('trace 视图不匹配');
  let previous=-1n;const errors=[];
  const steps=raw.steps.map((s,i)=>{
    const reverseAllowed=/^(return|reply|response|refill|hit|fault|返回|响应|回填|命中|异常)$/i.test(s?.type);
    let matches=s?.edgeId?candidates.filter(e=>e.id===s.edgeId):candidates.filter(e=>e.a===s?.a&&e.b===s?.b);
    if(!s?.edgeId && !matches.length && reverseAllowed)matches=candidates.filter(e=>e.kind==='port'&&e.a===s?.b&&e.b===s?.a);
    let reason=matches.length===0?'无法匹配':matches.length>1?'端口歧义，请指定 edgeId':'';
    if(s?.tick!==undefined){
      if(!(typeof s.tick==='string'&&/^\d+$/.test(s.tick)||Number.isSafeInteger(s.tick)&&s.tick>=0)||BigInt(s.tick)<previous)reason='tick 无效或逆序';
      else previous=BigInt(s.tick);
    }
    if(s?.edgeId&&matches.length===1&&(s.a!==undefined||s.b!==undefined)){
      const edge=matches[0];
      if(!(s.a===edge.a&&s.b===edge.b||reverseAllowed&&edge.kind==='port'&&s.b===edge.a&&s.a===edge.b))reason='edgeId 与端点不匹配';
    }
    if(s&&(!s.edgeId&&(!s.a||!s.b)||typeof s.text!=='string'||!s.text.trim()||typeof s.type!=='string'||!s.type.trim()))reason='缺少事件类型、描述或端点';
    if(reason)errors.push('步骤 '+(i+1)+' · '+reason+' · '+[s?.edgeId,s?.a,s?.b].filter(Boolean).join(' → '));
    const edge=matches[0];
    return {...s,a:s?.a??edge?.a,b:s?.b??edge?.b,edgeId:edge?.id,reverse:Boolean(edge && s?.a===edge.b && edge.a!==edge.b)};
  });
  if(errors.length)throw Error(errors.join('\n'));
  return {name:raw.name,steps};
}
function advance(i){
  if(!scene || i<0 || i>=scene.steps.length)return;
  position=i;const step=scene.steps[i],edge=edgeIndex.get(step.edgeId);
  if(view==='source' && edge){
    focus=edge.a;
    page=Math.floor(relations.filter(e=>e.a===focus||e.b===focus).findIndex(e=>e.id===edge.id)/8);
  }
  draw();
  $('event').textContent=(i+1)+' / '+scene.steps.length+'　'+eventEndpoints(step)+'　'+step.type+(step.tick===undefined?'':'　t='+step.tick);
}
$('scenario').onchange=e=>selectScene(Number(e.target.value));
$('step').onclick=()=>{stop();if(scene)advance((position+1)%scene.steps.length)};
$('play').onclick=()=>{
  if(timer){stop();return}
  if(!scene)return;
  if(position===scene.steps.length-1)advance(0);
  $('play').textContent='Ⅱ 暂停';
  timer=setInterval(()=>{
    if(position+1<scene.steps.length)advance(position+1);
    if(position===scene.steps.length-1)stop();
  },1100);
};
$('home').onclick=()=>model.architecture?showArchitecture():openView(model.view.id);$('view').onchange=e=>openView(e.target.value);
$('configuration').onchange=e=>{
  configSelection.set($('model').value,e.target.value);activate(view);
};
$('model').onchange=()=>activate();$('scope').onchange=e=>{replayMemory.clear();importedScenes.clear();scene=null;scope=e.target.value;search();if(objects.get(focus)?.kind==='instance'&&!scoped(focus))focus=scope;openView(view)};
$('search').oninput=search;$('object').onchange=e=>{if(e.target.value){focus=e.target.value;openView('source')}};
$('prev').onclick=()=>{page--;draw()};$('nextPage').onclick=()=>{page++;draw()};
$('minus').onclick=()=>{zoom=Math.max(.5,zoom-.15);draw()};$('plus').onclick=()=>{zoom=Math.min(2.5,zoom+.15);draw()};
importFile('file',(raw,name)=>register(name,raw));
importFile('trace',(raw,file)=>{
  const target=raw.viewId || (raw.graph && raw.graph!==model.name ? raw.graph : view);
  if(!Array.from($('view').options).some(o=>o.value===target))throw Error('未知视图 '+target);
  const next={...bindTrace(raw,replayEligibility(target).edges,target),id:'imported',origin:'导入 · '+file};
  importedScenes.set(target,next);
  openView(target);
  selectScene(choices.indexOf(next));
});

