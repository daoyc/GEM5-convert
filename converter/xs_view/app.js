const $=id=>document.getElementById(id);
const NS='http://www.w3.org/2000/svg';
function svg(tag,attrs,parent,caption){
  const e=document.createElementNS(NS,tag);
  for(const [key,val] of Object.entries(attrs))e.setAttribute(key,val);
  if(caption!==undefined)e.textContent=caption;
  parent.append(e);return e;
}
let graph,stream,index,timer,zoom,selected;
const sessions=new Map();
function inspect(n){
  const h=document.createElement('h2'),p=document.createElement('p');
  h.textContent=n.title;p.textContent=n.detail;$('info').replaceChildren(h,p,source(n.path));
}
function stop(){clearInterval(timer);timer=null;$('play').textContent='▶ 播放'}
function go(id){location.hash=id==='overview'?'overview':encodeURIComponent(id);openGraph()}
function openGraph(keep){
  if(!overview)return;
  const id=location.hash.slice(1),g=graphFor(Object.hasOwn(modules,id)?modules[id]:overview);
  if(graph===g)return;
  if(graph)sessions.set(graph,{choice:$('scenario').value,index,selected,imported:graph.imported});
  stop();graph=g;zoom=1;mobileFull=g.id==='overview';
  const deep=g.id!=='overview', saved=sessions.get(g);
  const label=deep?g.title:'架构总览';
  $('heading').textContent=deep?label:'昆明湖 V3 · 架构总览';
  $('home').classList.toggle('on',!deep);$('deep').value=deep?id:'';
  $('mapping').hidden=!deep;
  if(deep){$('modelText').textContent=(profile?'源码默认结构对照 · ':'')+g.mapping;$('rtl').hidden=!/^https?:\/\//.test(g.rtl||'');if(!$('rtl').hidden)$('rtl').href=g.rtl}
  $('references').replaceChildren(...[...g.nodes, ...g.edges.filter(e=>!e.legacy)].map(item=>{
    const li=document.createElement('li');li.append(source(item.path,item.title||item.label));return li;
  }));
  $('count').textContent=g.nodes.length+' NODES　/　'+g.edges.filter(e=>!e.legacy).length+' LINKS';
  $('scenario').replaceChildren(...g.streams.map((s,i)=>new Option(s.name,i)));
  if(g.imported)$('scenario').add(new Option(g.imported.name,'imported'));
  $('scenario').value=saved?.choice||'0';selected=g.nodes.find(n=>n.id===keep&&!n.reason)?.id||saved?.selected||g.nodes.find(n=>n.role==='internal')?.id||g.nodes[0].id;
  $('msg').textContent=g.excluded.length?'配置未匹配的场景 · '+g.excluded.join('、'):'';drawParams();selectStream(saved?.index||0);inspect(g.nodes.find(n=>n.id===selected));window.scrollTo(0,0);
}
function selectStream(offset=0){
  stop();stream=graph.streams[$('scenario').value]||graph.imported;index=offset;
  $('play').disabled=$('next').disabled=!stream; $('scenario').disabled=!stream;
  $('badge').textContent=!stream?'无适用场景':stream===graph.imported?'导入 · '+graph.filename:'源码演示';
  $('scenarioSource').replaceChildren(...(stream?.path?[source(stream.path,'场景源码')]:[]));render();
}
function jump(i){stop();index=i;render();followEvent()}
let sceneOnly=false, mobileFull=false;
const smallScreen=matchMedia('(max-width:700px)');
const families=[
  ['前端','FRONT END','#84c3ff','#172e45'],
  ['后端','BACK END','#c3abfa','#2c2940'],
  ['访存与翻译','LOAD / STORE','#f1c98e','#332f30'],
  ['存储层次','MEMORY','#8fdbc7','#193636']
];
function wirePath(points){
  const corners=points.filter((p,i)=>!i||i===points.length-1||
    (points[i-1][0]!==points[i+1][0]&&points[i-1][1]!==points[i+1][1]));
  let d='M'+corners[0].join(' ');
  for(let i=1;i<corners.length-1;i++){
    const [x,y]=corners[i],[a,b]=corners[i-1],[u,v]=corners[i+1];
    const r=Math.min(8,(Math.abs(a-x)+Math.abs(b-y))/2,(Math.abs(u-x)+Math.abs(v-y))/2);
    d+='L'+(x+r*Math.sign(a-x))+' '+(y+r*Math.sign(b-y))+'Q'+x+' '+y+' '+(x+r*Math.sign(u-x))+' '+(y+r*Math.sign(v-y));
  }
  return d+'L'+corners.at(-1).join(' ');
}
// Use only the arrows actually drawn, including the direction of a replay response.
const diagram=$('diagram');
let pointerPosition=null;
function showNeighbors(center){
  const id=center?.dataset.node;
  const incoming=new Set(), outgoing=new Set();
  for(const edge of diagram.querySelectorAll('.edge')){
    const {from,to}=edge.dataset;
    const relation=!id?'':to===id?'up':from===id?'down':'other';
    edge.dataset.relation=relation;
    if(relation==='up')incoming.add(from);
    if(relation==='down')outgoing.add(to);
  }
  for(const node of diagram.querySelectorAll('.node')){
    const peer=node.dataset.node;
    node.dataset.relation=!id?'':peer===id?'center':incoming.has(peer)&&outgoing.has(peer)?'both':
      incoming.has(peer)?'up':outgoing.has(peer)?'down':'other';
  }
  $('relationKey').hidden=!id;
  $('status').hidden=Boolean(id);
}
function focusedNode(){return diagram.querySelector('.node:focus-visible')}
function updateNeighbors(){
  const hovered=pointerPosition && document.elementFromPoint(...pointerPosition)?.closest('#diagram .node');
  showNeighbors(hovered||focusedNode());
}
diagram.addEventListener('pointermove',e=>{
  if(e.pointerType==='touch')return;
  pointerPosition=[e.clientX,e.clientY];
  const node=e.target.closest('.node')||focusedNode();
  if((node?.dataset.node||'')!==(diagram.querySelector('[data-relation="center"]')?.dataset.node||''))showNeighbors(node);
});
diagram.addEventListener('pointerleave',()=>{pointerPosition=null;showNeighbors(focusedNode())});
diagram.addEventListener('focusin',()=>showNeighbors(focusedNode()));
diagram.addEventListener('focusout',()=>queueMicrotask(updateNeighbors));
function render(){
  const root=$('diagram'),geo=prepareGraph(graph);
  const compact=Boolean(stream)&&smallScreen.matches&&!mobileFull;
  $('mobileView').textContent=mobileFull?'当前事件':'完整拓扑';
  $('mobileView').setAttribute('aria-pressed',String(mobileFull));
  document.querySelector('.board').classList.toggle('compact',compact);
  const priorFocus=document.activeElement?.closest('.node')?.getAttribute('aria-label');
  root.replaceChildren();root.setAttribute('viewBox','0 0 1000 '+geo.height);
  root.style.width=(100*zoom)+'%';root.style.minWidth=(900*zoom)+'px';root.style.maxHeight='none';
  $('scale').textContent=Math.round(100*zoom)+'%';
  const defs=svg('defs',{},root);
  for(const [id,color] of [['normal','#8295a9'],['current','#92ffe0'],['up','#8bcaff'],['down','#ffca82']]){
    const m=svg('marker',{id,viewBox:'0 0 10 10',refX:0,refY:5,markerUnits:'userSpaceOnUse',markerWidth:8,markerHeight:8,orient:'auto'},defs);
    svg('path',{d:'M0 0L10 5L0 10Z',fill:color},m);
  }
  if(!compact&&graph.id==='overview'){
    families.forEach(([label,english,accent,fill],i)=>{
      const y=i*112+3;
      svg('rect',{x:5,y,width:990,height:106,rx:8,fill,'fill-opacity':.86,stroke:accent,'stroke-opacity':.19},root);
      svg('rect',{x:24,y:y+9,width:4,height:11,rx:2,fill:accent},root);
      svg('text',{x:34,y:y+19,'font-size':12,fill:accent,'font-weight':650},root,label);
      svg('text',{x:label.length*13+43,y:y+18,'font-family':'Consolas,monospace','font-size':9,'letter-spacing':1.1,fill:accent},root,english);
    });
  }
  if(!compact&&geo.boundary){
    svg('rect',{...geo.boundary,rx:10,fill:'#24374b','fill-opacity':.8,stroke:'#7c9bac','stroke-dasharray':'6 4'},root);
    for(const [x,label] of [[22,'上游接口'],[geo.boundary.x+12,'模型内部 · '+graph.title.split('·')[0]],[812,'下游接口']])
      svg('text',{x,y:17,'font-size':12,fill:'#b7cedd'},root,label);
  }
  const step=stream?.steps[index]||{},node=id=>graph.nodes.find(n=>n.id===id);
  const active=step.edgeId?graph.edges.find(e=>e.id===step.edgeId):
    graph.edges.find(e=>e.a===step.a&&e.b===step.b)||graph.edges.find(e=>e.a===step.b&&e.b===step.a);
  const direct=active?.a===step.a;
  $('status').textContent=!stream?'当前配置缺少场景所需的组件或开关':(index+1)+' / '+stream.steps.length+'　'+node(step.a).title+' → '+node(step.b).title+'　'+step.type;
  let visibleNodes=graph.nodes;
  if(compact){
    root.setAttribute('viewBox','0 0 394 124');root.style.minWidth='0';root.style.width='100%';
    const start=node(step.a),end=node(step.b);
    visibleNodes=[{...start,x:9,y:46},{...end,x:220,y:46}];
    svg('text',{x:12,y:28,fill:'#ffca82','font-size':13},root,'发送端');
    svg('text',{x:220,y:28,fill:'#92ffe0','font-size':13},root,'接收端');
  }
  for(const edge of compact?[active]:[...graph.edges.filter(e=>e!==active&&!e.legacy),...(active?[active]:[])]){
    const hot=edge===active,points=geo.paths.get(edge);
    const coords=compact?[[174,78],[220,78]]:hot&&!direct?[...points].reverse():points;
    const inScene=stream?.steps.some(s=>s.edgeId?s.edgeId===edge.id:(s.a===edge.a&&s.b===edge.b)||(s.b===edge.a&&s.a===edge.b));
    if((sceneOnly&&stream&&!inScene)||graph.blocked.has(edge.a)||graph.blocked.has(edge.b))continue;
    // End the shaft at the centre of the arrow base. The tip lands on the port.
    const tip=coords.at(-1), previous=coords.at(-2);
    const base=[tip[0]-8*Math.sign(tip[0]-previous[0]),tip[1]-8*Math.sign(tip[1]-previous[1])];
    const d=wirePath([...coords.slice(0,-1),base]);
    const group=svg('g',{class:'edge','data-edge':edge.id,'data-from':hot?step.a:edge.a,'data-to':hot?step.b:edge.b},root);svg('title',{},group,edge.label);
    svg('path',{d,fill:'none',stroke:'transparent','stroke-width':10},group);
    svg('path',{d,fill:'none',class:'wire',stroke:hot?'#92ffe0':inScene?'#a1acbc':'#748496','stroke-width':hot?3:1.6,'marker-end':'url(#'+(hot?'current':'normal')+')'},group);
    const first=coords[0];
    svg('circle',{cx:first[0],cy:first[1],r:hot?4:2.8,fill:hot?'#ffca82':'#233546',stroke:hot?'#ffca82':'#8fa1b1','stroke-width':1.2},group);
    if(hot){const dot=svg('circle',{r:3.5,fill:'#fbfffd',class:'flow-dot'},group);svg('animateMotion',{dur:'1.35s',repeatCount:'indefinite',path:d},dot)}
    group.setAttribute('role','button');group.setAttribute('tabindex','0');
    group.onclick=()=>inspect({title:edge.label,detail:node(edge.a).title+' → '+node(edge.b).title+' · 架构逻辑流 · '+edge.id,path:edge.path});
    group.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();group.onclick()}};
  }
  const symbols={
    bpu:'M2 15V9h6V3m0 6h7V5m-3 0h3v3',ftq:'M2 3h13v3H2zM2 9h13M2 13h9',
    ifu:'M2 4h6v10H2zM9 9h7m-3-3 3 3-3 3',icache:'M2 3h13v11H2zM5 6h7M5 9h7',
    decode:'M2 3h4v10H2zM9 4h6M9 8h4M9 12h6',rename:'M2 4h5l4 8h4M2 12h4l2-3M10 6l2-2h3',
    dispatch:'M2 8h5m0 0 4-5h4M7 8h8M7 8l4 5h4',iew:'M9 1 3 10h5l-1 5 7-10H9z',
    commit:'M2 3h11v4M2 3v11h6m0-4 3 3 5-6',lsu:'M4 2v11l-3-3m3 3 3-3M12 14V3l-3 3m3-3 3 3',
    mmu:'M1 3h6v5H1zM9 9h6v5H9zM7 5h5v4',dcache:'M2 3h13v11H2zM5 6h3v5H5zM10 6h2m-2 3h2',
    l2:'M1 6l7-4 7 4-7 4zM1 10l7 4 7-4',llc:'M1 4l7-3 7 3-7 3zM1 8l7 3 7-3M1 12l7 3 7-3',
    fabric:'M1 4h4v4H1zM11 9h4v4h-4zM5 6h4v5h2',mem:'M2 4h12v8H2zM4 1v3m4-3v3m4-3v3M4 12v3m4-3v3m4-3v3'
  };
  for(const n of visibleNodes){
    const hot=n.id===step.b,focus=n.id===selected&&graph.id!=='overview';
    const g=svg('g',{transform:'translate('+n.x+' '+n.y+')',class:n.reason?'node unavailable':'node','data-node':n.id,role:'button',tabindex:0,'aria-label':n.title},root);
    svg('title',{},g,n.sub+' · '+(n.target?'进入模块':'查看实现'));
    const from=n.id===step.a;
    const accent=graph.id==='overview'?families[n.band][2]:n.role==='internal'?'#a8c6ee':'#94cbbf';
    const border=hot?'#92ffe0':from?'#ffca82':focus?'#bad5ff':'#5e7082';
    svg('rect',{x:3,y:4,width:162,height:62,rx:9,fill:'#0b1420','fill-opacity':.46},g);
    svg('rect',{class:'card',width:165,height:64,rx:9,fill:hot?'#22463f':from?'#423932':'#223142',stroke:border,'stroke-width':from||hot?2:1.2},g);
    svg('rect',{x:10,y:8,width:23,height:23,rx:5,fill:accent,'fill-opacity':.13},g);
    svg('path',{d:symbols[n.target||n.id]||'M2 3h12v10H2zM5 6h6m-6 3h4',transform:'translate(13.5 11.5)',fill:'none',stroke:accent,'stroke-width':1.45,'stroke-linecap':'round','stroke-linejoin':'round'},g);
    const name=svg('text',{x:39,y:25,'font-size':15,'font-weight':650,fill:'#f2f6fb'},g,n.title);
    if(name.getComputedTextLength()>104){name.setAttribute('textLength',104);name.setAttribute('lengthAdjust','spacingAndGlyphs')}
    if(n.target)svg('text',{x:147,y:24,fill:'#a5b7c9','font-size':13},g,'↗');
    const sub=svg('text',{x:12,y:49,'font-size':11.5,fill:'#bdcbd8'},g,n.sub);
    const max=hot||from?100:142;
    if(sub.getComputedTextLength()>max){sub.setAttribute('textLength',max);sub.setAttribute('lengthAdjust','spacingAndGlyphs')}
    if(from||hot)svg('text',{x:151,y:50,'text-anchor':'end','font-weight':700,'font-size':11,fill:border},g,from?'发出':'接收');
    const act=()=>{if(n.target){go(n.target);return}selected=n.id;inspect(n);render();root.querySelectorAll('.node')[visibleNodes.indexOf(n)].focus({preventScroll:true})};
    g.onclick=act;g.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();act()}};
  }
    if(priorFocus)Array.from(root.querySelectorAll('.node')).find(el=>el.getAttribute('aria-label')===priorFocus)?.focus({preventScroll:true});
  updateNeighbors();
  $('log').replaceChildren(...(stream?.steps||[]).map((s,i)=>{
    const li=document.createElement('li'),btn=document.createElement('button');btn.className=i===index?'active':'';
    btn.textContent=String(i+1).padStart(2,'0')+'　'+s.type+'　 '+node(s.a).title+' → '+node(s.b).title+(s.tick==null?'':'　t='+s.tick);
    if(i===index)btn.textContent+='　'+s.text;btn.onclick=()=>{jump(i);document.querySelector('#log .active')?.focus({preventScroll:true})};li.append(btn);return li;
  }));
}
function followEvent(){
  if(!stream)return;
  const list=$('log'),btn=list.querySelector('.active');
  if(btn)list.scrollTop+=btn.getBoundingClientRect().top-list.getBoundingClientRect().top-list.clientHeight/2+btn.clientHeight/2;
  const canvas=document.querySelector('.canvas'),step=stream.steps[index];
  if((smallScreen.matches&&!mobileFull)||canvas.scrollWidth<=canvas.clientWidth)return;
  const rect=id=>{const i=graph.nodes.findIndex(n=>n.id===id);return $('diagram').querySelectorAll('.node')[i].getBoundingClientRect()};
  const a=rect(step.a),b=rect(step.b),v=canvas.getBoundingClientRect();
  const left=Math.min(a.left,b.left),right=Math.max(a.right,b.right);
  const center=right-left<=canvas.clientWidth?(left+right)/2:(b.left+b.right)/2;
  canvas.scrollLeft+=center-v.left-v.width/2;
  canvas.scrollTop+=(a.top+a.bottom+b.top+b.bottom)/4-v.top-v.height/2;
}
smallScreen.addEventListener('change',()=>{if(graph)render()});
$('mobileView').onclick=()=>{mobileFull=!mobileFull;$('mobileView').textContent=mobileFull?'当前事件':'完整拓扑';$('mobileView').setAttribute('aria-pressed',String(mobileFull));render();followEvent()};
$('wires').onclick=()=>{sceneOnly=!sceneOnly;$('wires').setAttribute('aria-pressed',String(sceneOnly));render()};

$('home').onclick=()=>go('overview');$('deep').onchange=e=>go(e.target.value||'overview');
$('scenario').onchange=()=>selectStream();$('next').onclick=()=>jump((index+1)%stream.steps.length);
$('play').onclick=()=>{if(timer){stop();return}if(index===stream.steps.length-1)index=0;render();$('play').textContent='Ⅱ 暂停';
  timer=setInterval(()=>{if(index<stream.steps.length-1)index++;render();followEvent();if(index===stream.steps.length-1)stop()},1100)};
for(const [id,change] of [['minus',-.15],['plus',.15],['scale',0]])$(id).onclick=()=>{zoom=change?Math.min(2,Math.max(.7,zoom+change)):1;render()};
async function importFile(file){
  const g=graph;
  try{
    const s=await readTrace(file,g);if(graph!==g)return;
    if(s.steps.some(t=>g.blocked.has(t.a)||g.blocked.has(t.b)))throw Error("当前配置不支持该事件的端点");
    g.imported=s;g.filename=file.name;
    const list=$('scenario');if(list.options.length>g.streams.length)list.remove(list.options.length-1);
    list.add(new Option(s.name,'imported'));list.value='imported';selectStream();$('msg').textContent='已导入 '+s.steps.length+' 个事件';
  }catch(err){if(graph===g)$('msg').textContent=err.message}
}
$('upload').onchange=async e=>{const file=e.target.files[0];if(file)await importFile(file);e.target.value=''};
window.onhashchange=()=>{if(overview)openGraph()};










