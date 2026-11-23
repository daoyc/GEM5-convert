/* Draw logical ownership independently of the direction of a request or callback. */
function prepareGraph(g){
  if(g.geometry)return g.geometry;
  let height=500, boundary;
  if(g.id==='overview'){
    height=452;
    const rows=[
      ['bpu','ftq','ifu','icache'],['commit','iew','dispatch','rename','decode'],
      ['lsu','mmu','dcache'],['mem','fabric','llc','l2']
    ];
    rows.forEach((ids,row)=>ids.forEach((id,col)=>{
      const n=g.nodes.find(n=>n.id===id);
      n.x=Math.round(25+col*785/(ids.length-1));n.y=33+row*112;n.band=row;
    }));
  }
  else if(g.id==='mmu')boundary={x:202,y:28,width:605,height:405};
  else{
    const groups=['up','internal','down'].map(role=>g.nodes.filter(n=>n.role===role));
    const rows=Math.max(groups[0].length,Math.ceil(groups[1].length/2),groups[2].length,2);
    height=Math.max(365,rows*94+75);
    groups.forEach((nodes,col)=>{
      const double=col===1&&nodes.length>1, count=double?Math.ceil(nodes.length/2):nodes.length;
      nodes.forEach((n,i)=>{
        n.x=col===0?24:col===2?810:double?277+(i%2)*219:390;
        const row=double?Math.floor(i/2):i;
        n.y=Math.round(45+(row+.5)*(height-75)/count-32);
      });
    });
    boundary={x:228,y:30,width:510,height:height-48};
  }
  // Route through the spaces between cards. Search states distinguish the incoming axis.
  const paths=new Map();
  const xs=new Set([9,991]),ys=new Set([22,height-10]);
  for(const n of g.nodes){
    for(const x of [n.x-16,n.x+82,n.x+181])xs.add(x);
    for(const y of [n.y-16,n.y+32,n.y+80])ys.add(y);
  }
  const X=[...xs].sort((a,b)=>a-b),Y=[...ys].sort((a,b)=>a-b);
  const clear=(x,y)=>g.nodes.every(n=>x<n.x-5||x>n.x+170||y<n.y-5||y>n.y+69);
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
  const byId=new Map(g.nodes.map(n=>[n.id,n]));
  for(const e of g.edges)paths.set(e,routeEdge(byId.get(e.a),byId.get(e.b)));
  return g.geometry={height,boundary,paths};
}




