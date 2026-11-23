/* Structural source inventory and optional comparison, entirely local to this page. */
let comparison=null;
const coveragePanel=document.getElementById('coveragePanel');
function cell(tag,text,parent){
  const node=document.createElement(tag);
  node.textContent=text;
  parent.append(node);
  return node;
}
function readable(value){
  if(value==null)return '未知';
  if(typeof value==='boolean')return value?'启用':'关闭';
  return typeof value==='object'?JSON.stringify(value):String(value);
}
function runtimeCores(){
  const candidates=model.instances.filter(node=>/(?:^|\.)cpu\d*$/i.test(node.id)||/CPU$/i.test(node.fields?.type||''));
  const paths=new Set(candidates.map(node=>node.id));
  // A CPU can contain a CheckerCPU. Only the containing simulated core owns this scope.
  return candidates.filter(node=>{
    if(!scoped(node.id))return false;
    let parent=node.id;
    while(parent.includes('.')){
      parent=parent.slice(0,parent.lastIndexOf('.'));
      if(paths.has(parent))return false;
    }
    return true;
  });
}
function fieldAtCore(locator,cpu){
  const owner=locator.owner||'cpu';
  let path, nodes;
  if(owner==='system'||owner.startsWith('system.')){
    const parent=cpu.id.slice(0,Math.max(0,cpu.id.lastIndexOf('.')));
    let system=parent;
    while(system&&!/(?:^|\.)system$/i.test(system)&&!/System$/i.test(objects.get(system)?.fields?.type||'')){
      system=system.slice(0,Math.max(0,system.lastIndexOf('.')));
    }
    if(!system)return [];
    path=system+owner.slice(6);
  }else if(owner==='cpu'||owner.startsWith('cpu.')){
    path=cpu.id+owner.slice(3);
  }else return [];
  if(owner==='system.l2_caches'){
    const slot=cpu.id.match(/(\d+)$/)?.[1]||'0';
    nodes=[objects.get(path+slot)||(slot==='0'?objects.get(path):null)];
  }else if(owner==='system.mem_ctrls'){
    nodes=model.instances.filter(node=>node.id.startsWith(path)&&/^\d*$/.test(node.id.slice(path.length)));
  }else nodes=[objects.get(path)];
  return nodes.filter(node=>node?.fields&&Object.hasOwn(node.fields,locator.key)&&node.fields[locator.key]!=null)
              .map(node=>({path:node.id+'.'+locator.key,value:node.fields[locator.key]}));
}
function runtimeEvidence(record){
  if(!record.runtime||!model.config)return [];
  const fields=runtimeCores().flatMap(cpu=>fieldAtCore(record.runtime,cpu));
  return [...new Map(fields.map(field=>[field.path,field])).values()];
}
function featureState(item){
  if(!item?.requiresRuntime?.length)return '';
  if(!model.config)return (item.sourceEnabled??item.value)===true?'启用':(item.sourceEnabled??item.value)===false?'关闭':'未知';
  const states=runtimeCores().map(cpu=>{
    const outcomes=item.requiresRuntime.map(guard=>{
      const fields=fieldAtCore(guard,cpu);
      if(!fields.length)return null;
      return fields.every(field=>typeof guard.value==='boolean'?
        String(field.value).toLowerCase()===String(guard.value):String(field.value)===String(guard.value));
    });
    return outcomes.includes(false)?'关闭':outcomes.includes(null)?'未知':'启用';
  });
  if(!states.length)return '未知';
  return new Set(states).size===1?states[0]:'各核不同';
}
function inventoryRow(m){
  return {label:'子图组件',value:m.parts.map(p=>p.name).join('、'),origin:'源码结构',status:'已映射',evidence:m.evidence};
}
function graphRows(m){
  if(!m)return [];
  return m.coverage?.length?m.coverage:[inventoryRow(m)];
}
function recordKeys(rows){
  const counts=new Map();
  return new Map(rows.map(row=>{
    const n=counts.get(row.label)||0;
    counts.set(row.label,n+1);
    return [row.label+'#'+n,row];
  }));
}
function evidenceCell(tr,record,excerpts){
  const td=cell('td','',tr);
  if(!record){td.textContent='—';return}
  const entries=[[record.evidence,''],[record.defaultEvidence,'声明默认']];
  for(const item of record.overrides||[])entries.push([item.evidence,item.condition||'配置覆盖']);
  for(const item of record.evidenceChain||[])entries.push([item,'关联源码']);
  const seen=new Set();
  for(const [ev,caption] of entries){
    if(!ev?.file||!ev.line)continue;
    const loc=ev.file+':'+ev.line;
    if(seen.has(loc))continue;
    seen.add(loc);
    const details=document.createElement('details');
    td.append(details);cell('summary',caption?caption+' · '+loc:loc,details);
    cell('pre',excerpts?.[loc]||ev.text||loc,details);
  }
  if(!seen.size)td.textContent=record.evidence?.unresolved?'未定位':'—';
}
function printValue(row){
  if(!row)return '此模型清单未列出';
  return (row.condition?row.condition+' · ':'')+readable(row.value);
}
function drawCoverage(){
  if(!coveragePanel)return;
  coveragePanel.hidden=!model.view?.modules?.some(m=>m.coverage?.length)||view==='source';
  if(coveragePanel.hidden)return;
  const body=$('coverageRows'), header=$('coverageHead');
  body.replaceChildren();header.replaceChildren();
  const tableTitle= comparison?model.name+'（源码）':'源码值 / 条件';
  const cols=['模块 / 结构项','覆盖状态',tableTitle,'来源及依据'];
  if(model.config)cols.push('运行实例 · '+model.config);
  if(comparison)cols.push(comparison.name+'（源码）','对照依据');
  cols.forEach(name=>cell('th',name,header));
  const mods=new Map(model.view.modules.map(m=>[m.id,m]));
  const others=new Map((comparison?.view?.modules||[]).map(m=>[m.id,m]));
  const ids=view===model.view.id?new Set([...mods.keys(),...others.keys()]):[view];
  let visible=0;
  for(const id of ids){
    const m=mods.get(id),other=others.get(id);
    const left=recordKeys(graphRows(m)),right=recordKeys(graphRows(other));
    for(const key of new Set([...left.keys(),...right.keys()])){
      const row=left.get(key),r=right.get(key),item=row||r;
      const changed=comparison&&(!row||!r||['value','status','condition','origin'].some(k=>JSON.stringify(row[k])!==JSON.stringify(r[k])));
      if(comparison&&$('onlyDifferences').checked&&!changed)continue;
      if($('coverageFilter').value && item.status!==$('coverageFilter').value)continue;
      const tr=body.insertRow();tr.dataset.module=id;tr.dataset.label=item.label;
      if(changed)tr.className='diff-row';
      const name=cell('td','',tr);
      if(view===model.view.id&&m){
        const button=cell('button',m.name,name);button.onclick=()=>openView(id);
      }
      cell('span',item.label,name);cell('td',row?.status||'未列出',tr);
      const val=cell('td',printValue(row),tr);
      if(row?.requiresRuntime)cell('small','当前配置 · '+featureState(row),val);
      if(row?.origin)cell('small',row.origin,val);
      if(row?.defaultValue!==undefined)cell('small','声明默认 · '+readable(row.defaultValue),val);
      evidenceCell(tr,row,model.excerpts);
      if(model.config){
        const instances=runtimeEvidence(row||{});
        cell('td',instances.map(x=>x.path+' = '+readable(x.value)).join('\n')||(row?.runtime?'未导出':'—'),tr);
      }
      if(comparison){cell('td',printValue(r),tr);evidenceCell(tr,r,comparison.excerpts)}
      visible++;
    }
  }
  $('coverageCount').textContent=visible+' 项'+(comparison?' · '+model.name+' / '+comparison.name:'');
  $('onlyDiffLabel').hidden=!comparison;$('removeComparison').hidden=!comparison;
}
$('coverageFilter').onchange=drawCoverage;
$('onlyDifferences').onchange=drawCoverage;
$('removeComparison').onclick=()=>{comparison=null;drawCoverage()};
$('compareFile').onchange=async e=>{
  const f=e.target.files[0];if(!f)return;
  try{
    const text=(await f.text()).replace(/^\uFEFF/,'');
    const embedded=text.match(/<script\b[^>]*\bid=["']embedded["'][^>]*>([\s\S]*?)<\/script>/i);
    const data=JSON.parse(embedded?embedded[1]:text);
    if(!data.view?.modules?.some(m=>Array.isArray(m.coverage)))throw Error('所选文件缺少结构覆盖清单');
    comparison=data;$('onlyDifferences').checked=true;coveragePanel.open=true;drawCoverage();
  }catch(err){$('message').textContent='对照文件 · '+err.message}
  e.target.value='';
};

