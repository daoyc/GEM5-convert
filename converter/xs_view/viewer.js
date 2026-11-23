let overview, modules, sources, sourceParameters, sampleConfigs;
const sourceDialog=$('sourceDialog');
const objectsDialog=$('objectsDialog');

function source(location,label){
  const match=typeof location==='string'&&location.match(/^(.*?)(?::(\d+))?$/);
  const file=match?.[1]?.replace(/^GEM5\//,'');
  const line=Number(match?.[2]||1);
  if(!file||typeof sources?.[file]!=='string'){
    const span=document.createElement('span');
    span.textContent=(label||file||'源码')+' · 来源未定位';
    return span;
  }
  const link=document.createElement('a');
  link.href='#sourceDialog';link.textContent=(label||location)+' ↗';
  link.onclick=event=>{
    event.preventDefault();
    const lines=sources[file].split(/\r?\n/);
    const display=i=>String(i+1).padStart(5)+'  '+lines[i];
    const current=document.createElement('mark');
    current.className='selected';current.textContent=display(line-1);
    $('sourcePath').textContent=file+':'+line;
    $('sourceLines').replaceChildren(lines.slice(0,line-1).map((_,i)=>display(i)+'\n').join(''),
      current,'\n',lines.slice(line).map((_,i)=>display(i+line)).join('\n'));
    sourceDialog.showModal();
    current.scrollIntoView({block:'center'});
  };
  return link;
}

function decodeInstances(filename,text){
  if(filename.toLowerCase().endsWith('.ini')){
    const nodes=[];const ids=new Set();
    let node=null;
    for(const [i,line] of text.split(/\r?\n/).entries()){
      const value=line.trim();
      if(!value||value.startsWith('#')||value.startsWith(';'))continue;
      const section=value.match(/^\[([^\]]+)\]$/);
      if(section){
        if(ids.has(section[1]))throw Error('实例段重复 · '+section[1]);
        ids.add(section[1]);
        node={id:section[1],fields:Object.create(null)};nodes.push(node);continue;
      }
      const equals=value.indexOf('=');
      if(!node||equals<1)throw Error('INI 第 '+(i+1)+' 行缺少键值或实例段');
      node.fields[value.slice(0,equals).trim()]=value.slice(equals+1).trim();
    }
    return nodes.filter(n=>n.fields.type);
  }
  const json=JSON.parse(text);
  if(json?.format==='core-atlas/1'&&json.mode==='instances')return json.nodes;
  if(json?.format==='core-atlas/2')return json.instances;
  const nodes=[];
  function visit(obj){
    if(typeof obj?.path!=='string'||typeof obj.type!=='string')throw Error('config.json 根对象缺少 path 或 type');
    const fields=Object.create(null);nodes.push({id:obj.path,fields});
    for(const [key,val] of Object.entries(obj)){
      const values=Array.isArray(val)?val:[val];
      const children=values.filter(c=>c&&typeof c==='object'&&'path' in c&&'type' in c);
      if(children.length)children.forEach(visit);
      else fields[key]=val;
    }
  }
  visit(json);return nodes;
}

function inspector(){
  const embedded=$('source-browser');
  if(embedded){
    const frame=$('objectsFrame');
    if(!frame.hasAttribute('srcdoc'))frame.srcdoc=JSON.parse(embedded.textContent);
    objectsDialog.showModal();
  }else if(window.parent!==window){
    window.parent.postMessage({type:'core-atlas:inspect'},location.origin==='null'?'*':location.origin);
  }
}

$('objectsButton').onclick=inspector;
$('closeSource').onclick=()=>sourceDialog.close();
$('closeObjects').onclick=()=>objectsDialog.close();
$('closeHelp').onclick=()=>$('helpDialog').close();
$('traceHelp').onclick=()=>{
  const first=graph.edges.find(e=>!e.legacy);
  $('traceExample').textContent=JSON.stringify({name:'事件样例',viewId:graph.id,
    steps:[{edgeId:first.id,type:'request',text:first.label,tick:'100'}]},null,2);
  $('helpDialog').showModal();
};
let demoURL;
function setModel(model,samples){
  const architecture=model.architecture;
  if(!Array.isArray(architecture?.overview?.nodes)||!architecture.modules)throw Error('模型缺少昆明湖架构映射');
  overview=architecture.overview;modules=architecture.modules;sources=architecture.sources;
  sourceParameters=model.sourceParameters||{};sampleConfigs=samples||{};
  const warnings=[...(architecture.warnings||[])];
  let selectedKey='default';
  profileRegistry.clear();profileSerial=0;
  $('profile').length=3;
  if(model.instances?.length){
    try{
      const current=ProfileView.load({nodes:model.instances});
      selectedKey='conversion';profileRegistry.set(selectedKey,current);
      $('profile').add(new Option(model.config||'转换时运行配置',selectedKey));
    }catch(err){warnings.push(err.message)}
  }
  $('deep').replaceChildren(new Option('模块导航',''),...overview.nodes.filter(n=>Object.hasOwn(modules,n.id)).map(n=>new Option(n.title,n.id)));
  const diagnostics=$('diagnostics');
  diagnostics.hidden=!warnings.length;
  diagnostics.querySelector('summary').textContent=warnings.length+' 项来源待核对';
  diagnostics.querySelector('ul').replaceChildren(...warnings.map(w=>{
    const li=document.createElement('li');li.textContent=typeof w==='string'?w:JSON.stringify(w);return li;
  }));
  $('configSource').replaceChildren(source('GEM5/configs/example/kmhv3.py','kmhv3.py'));
  $('checkout').textContent=model.name;
  const first=overview.streams.find(s=>s.steps.length);
  const a=$('demoDownload');a.hidden=!first;
  if(demoURL)URL.revokeObjectURL(demoURL);
  if(first){
    const example={name:'接口验证样例 · '+first.name,viewId:overview.id,steps:first.steps.slice(0,2).map((s,i)=>({...s,tick:String(i)}))};
    demoURL=URL.createObjectURL(new Blob([JSON.stringify(example,null,2)],{type:'application/json'}));a.href=demoURL;
  }
  $('configMsg').textContent='';
  switchProfile(selectedKey,model.scope);
}

const embeddedModel=$('xs-model');
function loadModel(model,samples){
  try{setModel(model,samples)}catch(error){$('configMsg').textContent=error.message;console.error(error)}
}
if(embeddedModel){
  const data=JSON.parse(embeddedModel.textContent);
  loadModel(data.model,data.samples);
}else if(window.parent!==window){
  const origin=location.origin==='null'?'*':location.origin;
  window.addEventListener('message',event=>{
    if(event.source!==window.parent||event.origin!==location.origin||event.data?.type!=='core-atlas:model')return;
    loadModel(event.data.model,event.data.samples);
  });
  window.parent.postMessage({type:'core-atlas:ready'},origin);
}

