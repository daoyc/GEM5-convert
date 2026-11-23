async function readTrace(file,graph){
  const data=JSON.parse((await file.text()).replace(/^\uFEFF/,''));
  if(typeof data?.name!=='string'||!data.name.trim()||!Array.isArray(data.steps)||!data.steps.length)throw Error('回放需要名称和非空步骤');
  if((data.viewId!==undefined&&data.viewId!==graph.id)||(data.graph!==undefined&&data.graph!==graph.id)){
    throw Error('事件视图与当前视图 '+graph.id+' 不匹配');
  }
  const isReturn=/^(response|reply|return|refill|hit|fault|响应|返回|回填|命中|异常)$/i;
  let previous=-1n;
  const steps=data.steps.map((s,i)=>{
    const fail=detail=>{throw Error('事件 '+(i+1)+' · '+detail+' · '+[s?.a,s?.b,s?.edgeId].filter(Boolean).join(' → '))};
    if(typeof s?.type!=='string'||typeof s?.text!=='string'||!s.type.trim()||!s.text.trim())fail('缺少类型或描述');
    let {a,b,tick}=s;
    let edges=graph.edges.filter(e=>s.edgeId!==undefined?e.id===s.edgeId:e.a===a&&e.b===b);
    if(!edges.length&&s.edgeId===undefined&&isReturn.test(s.type))edges=graph.edges.filter(e=>e.a===b&&e.b===a);
    if(edges.length!==1)fail(edges.length?'端点存在歧义，请指定 edgeId':'找不到匹配边');
    const edge=edges[0];
    if(a===undefined&&b===undefined){a=edge.a;b=edge.b}
    else if(!(a===edge.a&&b===edge.b||a===edge.b&&b===edge.a&&isReturn.test(s.type)))fail('端点、方向或事件类型不匹配');
    if(tick!==undefined){
      if(!(typeof tick==='string'&&/^\d+$/.test(tick))&&!(Number.isSafeInteger(tick)&&tick>=0))fail('tick 无效');
      const current=BigInt(tick);
      if(current<previous)fail('tick 顺序冲突');
      previous=current;tick=String(tick);
    }
    return {a,b,type:s.type,text:s.text,tick,edgeId:edge.id};
  });
  return {name:data.name,steps};
}
