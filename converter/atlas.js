function scoped(path){
  if(!scope||scope==='root'||path===scope||path.startsWith(scope+'.'))return true;
  const cpu=scope.match(/^(.*)\.cpu(\d*)$/);
  if(!cpu||!path.startsWith(cpu[1]+'.'))return false;
  const name=path.slice(cpu[1].length+1).split('.')[0];
  if(/^cpu\d*$/.test(name))return false;
  const privateCache=name.match(/^(?:l2_caches|tol2bus_list)(\d*)$/);
  return !privateCache||Number(privateCache[1])===Number(cpu[2]);
}
function portInScope(edge){
  // A selected CPU includes its own private caches plus the shared fabric.
  if(/(?:^|\.)cpu\d*$/.test(scope||''))return scoped(edge.a)&&scoped(edge.b);
  return scoped(edge.a)||scoped(edge.b);
}
function owner(path){
  const parts=path.split('.').reverse();
  for(const part of parts){
    const m=model.view?.modules.find(m=>new RegExp('^(?:'+m.selector+')$','i').test(part));
    if(m)return m.id;
  }
}
function projected(){
  const output=[];
  for(const e of model.connections){
    if(e.kind!=='port'||!portInScope(e))continue;
    const endpointOwner=(path,port)=>owner(path)||(/\.cpu\d*$/.test(path)?({icache_port:'ifu',dcache_port:'lsu'}[port]):null);
    const a=endpointOwner(e.a,e.sourcePort?.port),b=endpointOwner(e.b,e.targetPort?.port);
    if(a&&b&&a!==b)output.push({...e,a,b,instanceA:e.a,instanceB:e.b});
  }
  return output;
}
function architectureEdges(){
  const groups=new Map();
  for(const edge of projected()){
    const key=edge.a+'>'+edge.b;
    if(!groups.has(key))groups.set(key,{...edge,id:'ports:'+key,label:'实例端口',members:[]});
    groups.get(key).members.push(edge);
  }
  return [...model.view.edges,...groups.values()];
}
function availableEdges(target=view){
  if(target==='source')return relations.filter(e=>e.kind==='port'&&portInScope(e));
  const mod=model.view.modules.find(m=>m.id===target);
  if(mod?.parts.some(p=>p.role))return mod.internalEdges||[];
  const all=[...model.view.edges,...projected().map(e=>({...e,a:e.instanceA,b:e.instanceB,moduleA:e.a,moduleB:e.b}))];
  if(target===model.view.id)return all;
  return [...all.filter(e=>[e.a,e.b,e.moduleA,e.moduleB].includes(target)),...(mod?.internalEdges||[])];
}
function moduleInfo(m){
  const matches=model.instances.filter(n=>scoped(n.id)&&new RegExp('^(?:'+m.selector+')$','i').test(n.id.split('.').pop()));
  const values={};
  for(const [k,p] of Object.entries(m.parameters)){
    values[k]={'声明默认':p.default||'未知','配置覆盖':p.override||'未知','配置有效值':p.value??'未知','运行实例':matches.length?matches.map(n=>({path:n.id,value:(k==='容量'?n.fields.size:n.fields.type)??'未知'})):'未知'};
    values[k]['当前有效值']=model.config?(matches.length?matches.map(n=>(k==='容量'?n.fields.size:n.fields.type)??'未知'):'未知'):(p.value??'未知');
    if(p.dynamic)values[k]['动态分支']=p.dynamic;
    if(p.selection)values[k]['选项来源']=p.selection;
  }
  showInfo(m.name,{'源码依据':m.evidence,'参数及来源':values,'实例匹配':matches.length?matches.map(n=>n.id):'未确认','内部组件':m.parts});
}
const BANDS=[
  {name:'前端',label:'FRONT END',accent:'#84c3ff',fill:'#172e45'},
  {name:'后端',label:'BACK END',accent:'#c3abfa',fill:'#2c2940'},
  {name:'访存与翻译',label:'LOAD / STORE',accent:'#f1c98e',fill:'#332f30'},
  {name:'存储层次',label:'MEMORY',accent:'#8fdbc7',fill:'#193636'}
];
const CARD_W=165, CARD_H=64, WIDTH=1000;
const names={bpu:'分支预测',ftq:'取指目标队列',ifu:'指令获取',decode:'指令译码',rename:'寄存器重命名',issue:'发射与执行',commit:'指令提交',lsu:'访存队列',mmu:'地址翻译',bus:'系统总线',mem:'内存控制'};
function moduleCaption(m){
  if(m.structureCaption&&(!model.config||!Object.keys(m.parameters).length))return m.structureCaption;
  const entry=Object.entries(m.parameters)[0];
  if(!entry)return names[m.id]||m.evidence?.file?.split('/').pop()||'';
  const [key,parameter]=entry;
  if(!model.config)return (key==='容量'?'容量 ':'')+(parameter.value??'未知');
  const matches=model.instances.filter(n=>scoped(n.id)&&owner(n.id)===m.id&&new RegExp('^(?:'+m.selector+')$','i').test(n.id.split('.').pop()));
  const values=[...new Set(matches.map(n=>key==='容量'?n.fields.size:n.fields.type).filter(v=>v!=null))];
  return values.length===1?((key==='容量'?'容量 ':'')+values[0]):values.length?'多个实例值':'实例值未知';
}

function overviewLayout(root,cards,modules){
  BANDS.forEach((band,i)=>{
    const row=modules.filter(m=>(m.id==='icache'?0:m.band)===i);
    if(i===1||i===3)row.reverse();
    const y=3+i*112;
    svg('rect',{x:5,y,width:990,height:106,rx:8,fill:band.fill,'fill-opacity':.86,stroke:band.accent,'stroke-opacity':.22},root);
    svg('rect',{x:24,y:y+9,width:4,height:11,rx:2,fill:band.accent},root);
    svg('text',{x:34,y:y+19,fill:band.accent,class:'band-label'},root,band.name);
    svg('text',{x:43+band.name.length*13,y:y+18,fill:band.accent,class:'band-legend'},root,band.label);
    row.forEach((m,col)=>cards.push({id:m.id,name:m.name,detail:moduleCaption(m),accent:band.accent,target:m.id,
      x:row.length===1?500:108+col*784/(row.length-1),y:y+62,click:()=>openView(m.id)}));
  });
  return 452;
}

function partInfo(part){
  showInfo(part.name,{'组件作用':part.description||part.name,'启用条件':part.condition,'当前配置':featureState(part)||null,'源码依据':part.evidence});
}
function moduleLayout(root,cards,edges,module,modules){
  const mapped=module.parts.some(p=>p.role);
  const parts=[...module.parts], links=[...(module.internalEdges||[])];
  // Older models encode their boundaries as overview relations to the module itself.
  if(!mapped){
    const incident=edges.filter(e=>e.a===view||e.b===view);
    for(const m of modules){
      if(m.id===view)continue;
      const input=incident.some(e=>e.a===m.id);
      if(input||incident.some(e=>e.b===m.id))parts.push({id:m.id,name:m.name,target:m.id,
        role:input?'up':'down',description:moduleCaption(m)});
    }
    parts.unshift({id:view,name:module.name,evidence:module.evidence,description:moduleCaption(module)});
    links.push(...incident);
  }
  const matches=new Set(model.instances.filter(n=>scoped(n.id)&&owner(n.id)===view&&new RegExp('^(?:'+module.selector+')$','i').test(n.id.split('.').pop())).map(n=>n.id));
  for(const e of model.connections){
    if(e.kind!=='containment'||!matches.has(e.a))continue;
    for(const id of [e.a,e.b]){
      if(parts.some(p=>p.id===id))continue;
      const object=objects.get(id);
      if(object)parts.push({id,name:id.split('.').pop(),description:object.fields.type,object});
    }
    links.push(e);
  }
  const groups=['up','internal','down'].map(role=>parts.filter(p=>(p.role||'internal')===role));
  // Keep parallel paths aligned when all internal components lie within
  // three request hops. Longer or disconnected pipelines use a compact grid.
  const internalIds=new Set(groups[1].map(p=>p.id)), depth=new Map();
  let frontier=groups[0].map(p=>p.id);
  for(let d=0;d<3&&frontier.length;d++){
    const next=[];
    for(const edge of links){
      if(frontier.includes(edge.a)&&internalIds.has(edge.b)&&!depth.has(edge.b)){
        depth.set(edge.b,d);next.push(edge.b);
      }
    }
    frontier=next;
  }
  const tiers=depth.size===internalIds.size?Array.from({length:3},(_,d)=>groups[1].filter(p=>depth.get(p.id)===d)).filter(col=>col.length):[];
  const layered=tiers.length>=2;
  const middleRows=layered?Math.max(...tiers.map(col=>col.length)):Math.ceil(groups[1].length/2);
  const height=Math.max(348,80+Math.max(groups[0].length,middleRows,groups[2].length)*95);
  const left=layered&&tiers.length===3?208:228;
  svg('rect',{x:left,y:30,width:1000-2*left,height:height-48,rx:10,fill:'#24374b','fill-opacity':.8,stroke:'#7c9bac','stroke-dasharray':'6 4'},root);
  for(const [x,label] of [[22,'上游接口'],[left+12,'模型内部 · '+module.name],[812,'下游接口']])
    svg('text',{x,y:19,class:'band-label',fill:'#b7cedd'},root,label);
  groups.forEach((group,column)=>{
    const twoCols=column===1&&group.length>1;
    group.forEach((p,i)=>{
      let x=column===0?106:column===2?893:twoCols?368+(i%2)*230:490;
      let rows=twoCols?Math.ceil(group.length/2):group.length,row=twoCols?Math.floor(i/2):i;
      if(column===1&&layered){
        const d=depth.get(p.id);
        x=tiers.length===3?303+198*d:368+230*d;
        rows=tiers[d].length;row=tiers[d].indexOf(p);
      }
      const y=47+(row+.5)*(height-76)/rows;
      cards.push({id:p.id,name:p.name,detail:p.requiresRuntime?'条件路径 · '+featureState(p):p.description||p.evidence?.file?.split('/').pop()||'',target:p.target,x,y,
        accent:column===1?BANDS[module.band].accent:'#94cbbf',
        click:()=>p.target?openView(p.target):p.object?inspectObject(p.object):partInfo(p)});
    });
  });
  return {height,edges:links};
}
// Route along gutters shared by card ports, with bend and channel-occupancy costs.
// Cache by geometry so the graph can repaint every playback step without rerouting.
let lastRouting;
function routeWires(cards,edges,height){
  const nodes=cards.map(n=>({...n,x:n.x-CARD_W/2,y:n.y-CARD_H/2}));
  const signature=JSON.stringify([height,nodes.map(n=>[n.id,n.x,n.y]),edges.map(e=>[e.id,e.a,e.b])]);
  if(lastRouting?.signature===signature)return lastRouting.paths;
  const paths=new Map();
  const xs=new Set([9,991]),ys=new Set([22,height-10]);
  for(const n of nodes){
    for(const x of [n.x-16,n.x+82,n.x+181])xs.add(x);
    for(const y of [n.y-16,n.y+32,n.y+80])ys.add(y);
  }
  const X=[...xs].sort((a,b)=>a-b),Y=[...ys].sort((a,b)=>a-b);
  const clear=(x,y)=>nodes.every(n=>x<n.x-5||x>n.x+170||y<n.y-5||y>n.y+69);
  const grid=Y.flatMap(y=>X.map(x=>clear(x,y)));
  const pos=(x,y)=>Y.indexOf(y)*X.length+X.indexOf(x);
  const point=i=>[X[i%X.length],Y[Math.floor(i/X.length)]];
  function ports(n){
    return [[n.x-16,n.y+32,n.x,n.y+32],[n.x+181,n.y+32,n.x+165,n.y+32],
      [n.x+82,n.y-16,n.x+82,n.y],[n.x+82,n.y+80,n.x+82,n.y+64]];
  }
  const occupied=new Map();
  const segment=(a,b)=>Math.min(a,b)+','+Math.max(a,b);
  function routeEdge(a,b){
    const starts=ports(a),ends=ports(b), costs=new Map(),prev=new Map(),queue=[];
    for(const [x,y] of starts){const k=pos(x,y)*3;costs.set(k,0);queue.push([0,k])}
    while(queue.length){
      queue.sort((a,b)=>b[0]-a[0]);
      const [cost,key]=queue.pop();if(cost!==costs.get(key))continue;
      const i=Math.floor(key/3),axis=key%3,[x,y]=point(i);
      const end=ends.find(p=>p[0]===x&&p[1]===y);
      if(end){
        const points=[end.slice(2)];let k=key;
        while(k!==undefined){points.push(point(Math.floor(k/3)));k=prev.get(k)}
        const start=starts.find(p=>p[0]===points.at(-1)[0]&&p[1]===points.at(-1)[1]);
        for(let j=1;j<points.length-1;j++){
          const seg=segment(pos(...points[j]),pos(...points[j+1]));
          occupied.set(seg,(occupied.get(seg)||0)+1);
        }
        points.push(start.slice(2));return points.reverse();
      }
      for(const [j,dir] of [[i-1,1],[i+1,1],[i-X.length,2],[i+X.length,2]]){
        if(!grid[j]||(dir===1&&Math.floor(i/X.length)!==Math.floor(j/X.length)))continue;
        const [u,v]=point(j);
        if(!clear((x+u)/2,(y+v)/2))continue;
        const weight=cost+8*(occupied.get(segment(i,j))||0)+Math.abs(x-u)+Math.abs(y-v)+(axis&&axis!==dir?19:0);
        const next=j*3+dir;
        if(weight<(costs.get(next)??Infinity)){costs.set(next,weight);prev.set(next,key);queue.push([weight,next])}
      }
    }
    throw Error('Topology routing failed: '+a.id+' → '+b.id);
  }
  const byId=new Map(nodes.map(n=>[n.id,n]));
  for(const e of edges){
    const a=byId.get(e.a),b=byId.get(e.b);
    if(a&&b)paths.set(e.id,routeEdge(a,b));
  }
  lastRouting={signature,paths};
  return paths;
}

function roundedWire(coords){
  const tip=coords.at(-1),prev=coords.at(-2);
  const base=[tip[0]-8*Math.sign(tip[0]-prev[0]),tip[1]-8*Math.sign(tip[1]-prev[1])];
  const pts=[...coords.slice(0,-1),base].reduce((out,p)=>{
    const [a,b]=out.slice(-2);
    if(a&&b&&((a[0]===b[0]&&p[0]===b[0])||(a[1]===b[1]&&p[1]===b[1])))out.pop();
    out.push(p);return out;
  },[]);
  let d='M'+pts[0].join(' ');
  for(let i=1;i<pts.length-1;i++){
    const [x,y]=pts[i],[u,v]=pts[i-1],[a,b]=pts[i+1];
    const r=Math.min(8,(Math.abs(u-x)+Math.abs(v-y))/2,(Math.abs(a-x)+Math.abs(b-y))/2);
    d+=' L'+(x+r*Math.sign(u-x))+' '+(y+r*Math.sign(v-y))+' Q'+x+' '+y+' '+(x+r*Math.sign(a-x))+' '+(y+r*Math.sign(b-y));
  }
  return d+' L'+base.join(' ');
}

const mapDiagram=$('map');
let pointerPosition=null;
function showNeighbors(center){
  const id=center?.dataset.node, upstream=new Set(),downstream=new Set();
  for(const edge of mapDiagram.querySelectorAll('.edge')){
    const {from,to}=edge.dataset,relation=!id?'':to===id?'up':from===id?'down':'other';
    edge.dataset.relation=relation;
    if(relation==='up')upstream.add(from);
    if(relation==='down')downstream.add(to);
  }
  for(const n of mapDiagram.querySelectorAll('.node')){
    const peer=n.dataset.node;
    n.dataset.relation=!id?'':peer===id?'center':upstream.has(peer)&&downstream.has(peer)?'both':
        upstream.has(peer)?'up':downstream.has(peer)?'down':'other';
  }
  if($('relationKey'))$('relationKey').hidden=!id;
  $('event').hidden=!!id;
}
function refreshNeighbors(){
  const hovered=pointerPosition&&document.elementFromPoint(...pointerPosition)?.closest('#map .node');
  showNeighbors(hovered||mapDiagram.querySelector('.node:focus-visible'));
}
mapDiagram.addEventListener('pointermove',e=>{
  if(e.pointerType==='touch')return;
  pointerPosition=[e.clientX,e.clientY];
  const n=e.target.closest('.node')||mapDiagram.querySelector('.node:focus-visible');
  if(n!==mapDiagram.querySelector('[data-relation="center"]'))showNeighbors(n);
});
mapDiagram.addEventListener('pointerleave',()=>{pointerPosition=null;refreshNeighbors()});
mapDiagram.addEventListener('focusin',refreshNeighbors);
mapDiagram.addEventListener('focusout',()=>queueMicrotask(refreshNeighbors));

const glyphs={
  bpu:'M2 15V9h6V3m0 6h7V5m-3 0h3v3',ftq:'M2 3h13v3H2zM2 9h13M2 13h9',
  ifu:'M2 4h6v10H2zM9 9h7m-3-3 3 3-3 3',icache:'M2 3h13v11H2zM5 6h7M5 9h7',
  decode:'M2 3h4v10H2zM9 4h6M9 8h4M9 12h6',rename:'M2 4h5l4 8h4M2 12h4l2-3M10 6l2-2h3',
  issue:'M9 1 3 10h5l-1 5 7-10H9z',commit:'M2 3h11v4M2 3v11h6m0-4 3 3 5-6',
  lsu:'M4 2v11l-3-3m3 3 3-3M12 14V3l-3 3m3-3 3 3',mmu:'M1 3h6v5H1zM9 9h6v5H9zM7 5h5v4',
  dcache:'M2 3h13v11H2zM5 6h3v5H5zM10 6h2m-2 3h2',l2:'M1 6l7-4 7 4-7 4zM1 10l7 4 7-4',
  l3:'M1 4l7-3 7 3-7 3zM1 8l7 3 7-3M1 12l7 3 7-3',bus:'M1 4h4v4H1zM11 9h4v4h-4zM5 6h4v5h2',
  mem:'M2 4h12v8H2zM4 1v3m4-3v3m4-3v3M4 12v3m4-3v3m4-3v3'
};
let inspectorView,inspectorModel,inspectorScope;
function followMobileEvent(root){
  const canvas=root.parentElement;
  if(!matchMedia('(max-width:700px)').matches||canvas.scrollWidth<=canvas.clientWidth)return;
  const a=root.querySelector('[data-stream="send"]')?.getBoundingClientRect();
  const b=root.querySelector('[data-stream="receive"]')?.getBoundingClientRect();
  if(!a||!b)return;
  const left=Math.min(a.left,b.left),right=Math.max(a.right,b.right),viewport=canvas.getBoundingClientRect();
  const center=right-left+16<canvas.clientWidth?(left+right)/2:(b.left+b.right)/2;
  canvas.scrollLeft+=center-viewport.left-viewport.width/2;
  if(canvas.scrollHeight>canvas.clientHeight){
    const top=Math.min(a.top,b.top),bottom=Math.max(a.bottom,b.bottom);
    const mid=bottom-top+16<canvas.clientHeight?(top+bottom)/2:(b.top+b.bottom)/2;
    canvas.scrollTop+=mid-viewport.top-viewport.height/2;
  }
}
function draw(){
  const changed=inspectorView!==view||inspectorModel!==model||inspectorScope!==scope;
  inspectorView=view;inspectorModel=model;inspectorScope=scope;
  const prevFocus=document.activeElement?.closest('#map .node')?.dataset.node;
  const root=$('map');root.replaceChildren();const cards=[];let edges=[],height=404;
  const src=view==='source', overview=!src&&view===model.view.id;
  const modules=model.view?.modules||[],active=scene?.steps[position]?.edgeId;
  const module=modules.find(m=>m.id===view);
  $('prev').parentElement.hidden=!src;
  if(src){
    const n=objects.get(focus),adj=relations.filter(e=>e.a===focus||e.b===focus);
    $('object').value=focus;$('title').textContent=n.name;$('counts').textContent=adj.length+' 条直接关系';
    $('prev').disabled=page===0;$('nextPage').disabled=(page+1)*8>=adj.length;$('page').textContent=(page+1)+' / '+Math.max(1,Math.ceil(adj.length/8));
    edges=adj.slice(page*8,page*8+8);height=Math.max(180,edges.length*82+32);
    cards.push({id:focus,name:n.name,detail:n.kind||n.source,x:154,y:height/2,click:()=>inspectObject(n)});
    edges=edges.map((e,i)=>{
      const other=e.a===focus?e.b:e.a,obj=objects.get(other),key='peer:'+i;
      cards.push({id:key,name:obj?.name||other,detail:e.label,x:880,y:48+i*82,click:()=>{if(obj){focus=other;page=0;draw()}}});
      return {...e,a:e.a===focus?focus:key,b:e.a===focus?key:focus,original:e};
    });
    inspectObject(n);
  }else if(overview){
    $('title').textContent=model.name+' · 整核总览';
    edges=architectureEdges();
    $('counts').textContent=modules.length+' 个模块　/　'+edges.length+' 条连线';
    height=overviewLayout(root,cards,modules);
    if(changed)showInfo('CPU · '+model.name,{'源码依据':model.view.cpu,'配置入口':model.view.source,'配置覆盖证据':model.view.overrides,'未确认项':[...model.view.warnings,...(model.instances.length?model.view.modules.filter(m=>['bpu','mmu','icache','dcache','l2','l3','bus','mem'].includes(m.id)&&!model.instances.some(n=>scoped(n.id)&&owner(n.id)===m.id)).map(m=>m.name+' · 未匹配运行实例'):['尚未导入运行实例'])]});
  }else{
    $('title').textContent=module.name;$('counts').textContent='上下游边界与内部组件';
    ({height,edges}=moduleLayout(root,cards,architectureEdges(),module,modules));
    if(changed)moduleInfo(module);
  }
  root.setAttribute('viewBox','0 0 '+WIDTH+' '+height);root.style.width=(zoom*100)+'%';root.style.minWidth=(810*zoom)+'px';
  $('zoomValue').textContent=Math.round(zoom*100)+'%';
  const routes=routeWires(cards,edges,height),step=scene?.steps[position];
  let sending,receiving;
  const isActive=e=>e.id===active||e.members?.some(me=>me.id===active);
  for(const e of [...edges.filter(e=>!isActive(e)),...edges.filter(isActive)]){
    const route=routes.get(e.id);if(!route)continue;
    const member=e.members?.find(me=>me.id===active),hot=isActive(e);
    const reverse=hot&&(step.reverse||((e.original||e).b===step.a&&(e.original||e).a===step.b));
    const from=reverse?e.b:e.a,to=reverse?e.a:e.b;
    if(hot){sending=from;receiving=to}
    const points=reverse?[...route].reverse():route;
    const color=hot?'#92ffe0':e.kind==='port'?'#82beb0':'#8b9cae';
    const d=roundedWire(points),tip=points.at(-1),before=points.at(-2);
    const g=svg('g',{class:'edge'+(hot?' active':''),'data-edge':e.id,'data-from':from,'data-to':to,'aria-label':e.label},root);
    svg('title',{},g,e.label);
    svg('path',{d,fill:'none',stroke:'transparent','stroke-width':12},g);
    svg('path',{class:'wire',d,fill:'none',stroke:color,'stroke-width':hot?3:1.6},g);
    svg('path',{class:'arrow-head',d:'M0 0 l-8 -4 0 8 z',fill:color,transform:'translate('+tip.join(' ')+') rotate('+Math.atan2(tip[1]-before[1],tip[0]-before[0])*180/Math.PI+')'},g);
    svg('circle',{class:'port',cx:points[0][0],cy:points[0][1],r:hot?4:2.8,fill:hot?'#ffca82':'#25394c',stroke:hot?'#ffca82':color,'stroke-width':1.2},g);
    if(hot){
      const origin=svg('g',{transform:'translate('+points[0].join(' ')+')'},g);
      const localPath=roundedWire(points.map(([x,y])=>[x-points[0][0],y-points[0][1]]));
      const dot=svg('circle',{class:'flow-dot',r:3.6,fill:'#faffff','pointer-events':'none'},origin);
      svg('animateMotion',{dur:'0.85s',repeatCount:'indefinite',path:localPath,begin:'indefinite'},dot).beginElement();
    }
    button(g,()=>showInfo(e.label,{'关系类型':e.kind,'源码依据':e.evidence||'旧版模型','连接':member||e.members||e.original||e}));
  }
  for(const n of cards){
    const stream=sending===n.id?'send':receiving===n.id?'receive':'';
    const accent=n.accent||'#a8c6ee',border=stream==='send'?'#ffca82':stream?'#92ffe0':'#607487';
    const fill=stream==='send'?'#423932':stream?'#22463f':'#223142';
    const g=svg('g',{class:'node'+(stream?' active':''),'data-node':n.id,'data-stream':stream,
      transform:'translate('+(n.x-CARD_W/2)+' '+(n.y-CARD_H/2)+')','aria-label':n.name},root);
    svg('title',{},g,[n.name,n.detail,n.target?'进入模块':'查看源码'].filter(Boolean).join(' · '));
    svg('rect',{x:3,y:4,width:162,height:62,rx:9,fill:'#0b1420','fill-opacity':.46},g);
    svg('rect',{class:'card',width:CARD_W,height:CARD_H,rx:9,fill,stroke:border,'stroke-width':stream?2:1.2},g);
    svg('rect',{x:10,y:8,width:23,height:23,rx:5,fill:accent,'fill-opacity':.13},g);
    svg('path',{d:glyphs[n.target||n.id]||'M2 3h12v10H2zM5 6h6m-6 3h4',transform:'translate(13.5 11.5)',fill:'none',stroke:accent,'stroke-width':1.45,'stroke-linecap':'round','stroke-linejoin':'round'},g);
    const title=svg('text',{class:'node-name',x:39,y:25},g,n.name);
    const nameWidth=n.target?101:117;
    if(title.getComputedTextLength()>nameWidth){title.setAttribute('textLength',nameWidth);title.setAttribute('lengthAdjust','spacingAndGlyphs')}
    if(n.target)svg('text',{x:147,y:24,fill:'#a5b7c9','font-size':13},g,'↗');
    const desc=svg('text',{class:'node-detail',x:12,y:49},g,n.detail||'');
    // Keep full descriptions available on hover and in the inspector.
    const limit=stream?103:141, content=desc.textContent;
    if(desc.getComputedTextLength()>limit){
      let count=Math.min(30,content.length-1);
      do{desc.textContent=content.slice(0,count--)+'…'}while(count>0&&desc.getComputedTextLength()>limit);
    }
    if(stream)svg('text',{x:153,y:50,'text-anchor':'end',fill:border,'font-size':11,'font-weight':700},g,stream==='send'?'发出':'接收');
    button(g,n.click);
  }
  if(prevFocus)Array.from(root.querySelectorAll('.node')).find(n=>n.dataset.node===prevFocus)?.focus({preventScroll:true});
  followMobileEvent(root);
  refreshNeighbors();
  replayList();
}

function readConfig(raw,file){
  const instances=[],connections=new Map(),ids=new Set(),diagnostics=[];
  function visit(obj,parent){
    if(!obj||typeof obj.path!=='string'||typeof obj.type!=='string'||ids.has(obj.path))throw Error('config.json 实例路径或类型无效');
    ids.add(obj.path);const path=obj.path,evidence={file,path,origin:'运行实例'};
    const n={id:path,name:path,kind:'instance',fields:{},evidence};instances.push(n);
    if(parent!==undefined){const id='contains:'+JSON.stringify([parent,path]);connections.set(id,{id,a:parent,b:path,kind:'containment',label:'包含',evidence})}
    for(const [key,v] of Object.entries(obj)){
      if(v&&typeof v==='object'&&'peer' in v){
        const vector=Array.isArray(v.peer);(vector?v.peer:[v.peer]).forEach((peer,i)=>{
          const m=typeof peer==='string'&&peer.match(/^(.+)\.([^.[\]]+)(?:\[(\d+)\])?$/);
          if(!m||!['true','false'].includes(String(v.is_source).toLowerCase())){diagnostics.push(path+'.'+key+' · 对端或方向未知');return}
          let a={path,port:key,index:vector?i:null},b={path:m[1],port:m[2],index:m[3]===undefined?null:Number(m[3])};
          if(String(v.is_source).toLowerCase()==='false')[a,b]=[b,a];
          const id='port:'+JSON.stringify([a.path,a.port,a.index,b.path,b.port,b.index]);
          const label=p=>p.port+(p.index===null?'':'['+p.index+']');
          connections.set(id,{id,a:a.path,b:b.path,label:label(a)+' → '+label(b),kind:'port',sourcePort:a,targetPort:b,evidence:{...evidence,key,direction:'config.json'}});
        });
      }else{
        const children=(Array.isArray(v)?v:[v]).filter(c=>c&&typeof c==='object'&&'path' in c&&'type' in c);
        if(children.length)children.forEach(c=>visit(c,path));else n.fields[key]=v;
      }
    }
  }
  visit(raw);
  const declarations=new Map();
  for(const n of model.nodes){
    const type=n.fields.type?.replace(/^['"]|['"]$/g,'');if(type)declarations.set(type,declarations.has(type)?null:n.id);
  }
  for(const n of instances)n.declaration=declarations.get(n.fields.type);
  return {instances,connections:[...connections.values()],warnings:[...model.warnings,...diagnostics],config:file,scope:null};
}
importFile('config',(raw,file)=>{
  const key=$('model').value,versions=configurations.get(key),version='run:'+versions.size;
  const parsed=readConfig(raw,file);
  versions.set(version,{...versions.get('source'),...parsed});
  configSelection.set(key,version);activate(view);
});
const embedded=$('embedded');
if(embedded){
  register('included',JSON.parse(embedded.textContent));
}else if(location.protocol==='file:'){
  const link=document.createElement('a');
  link.href='index.html';link.textContent='打开已生成的架构页面';
  $('message').replaceChildren(link,'，或使用“导入模型”选择 JSON。');
}else{
  fetch('models/zenas-dev.json').then(response=>{
    if(!response.ok)throw Error('模型文件不可用');
    return response.json();
  }).then(data=>{if(!model)register('included',data)}).catch(()=>{
    if(!model)$('message').textContent='请导入转换器生成的模型 JSON。';
  });
}
