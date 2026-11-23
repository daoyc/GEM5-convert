/* The converter supplies the effective source values and source locations. */
const ProfileView = (() => {
  const specs = [
    ["commit","rob","cpu","numROBEntries","ROB 容量","项"],
    ["commit","rob","cpu","RobCompressPolicy","ROB 压缩策略",""],
    ["commit","retire","cpu","commitWidth","提交带宽","条/周期"],
    ["lsu","lq","cpu","LQEntries","Load Queue","项"],
    ["lsu","sq","cpu","SQEntries","Store Queue","项"],
    ["lsu","sb","cpu","SbufferEntries","Store Buffer","项"],
    ["lsu","replay","cpu","RARQEntries","RAR 队列","项"],
    ["lsu","replay","cpu","RAWQEntries","RAW 队列","项"],
    ["ifu","req","cpu","fetchWidth","取指宽度","条/周期"],
    ["ifu","pre","cpu","enablePredecode","预译码检查",""],
    ["ifu","req","cpu","fetchQueueSize","取指队列","项"],
    ["decode","input","cpu","decodeWidth","译码宽度","条/周期"],
    ["rename","map","cpu","renameWidth","重命名宽度","条/周期"],
    ["rename","alloc","cpu","numPhysIntRegs","整数物理寄存器","个"],
    ["rename","alloc","cpu","numPhysFloatRegs","浮点物理寄存器","个"],
    ["dispatch","admit","cpu","enableDispatchStage","独立分派级",""],
    ["dispatch","select","cpu","numDQEntries","分派队列深度","项/队列"],
    ["iew","wb","cpu","wbWidth","写回宽度","条/周期"],
    ["ftq","entries","branchPred","ftq_size","FTQ 容量","项/线程"],
    ["bpu","components","branchPred.ubtb","enabled","ubtb",""],
    ["bpu","components","branchPred.abtb","enabled","abtb",""],
    ["bpu","components","branchPred.microtage","enabled","microtage",""],
    ["bpu","mbtb","branchPred.mbtb","enabled","mbtb",""],
    ["bpu","components","branchPred.tage","enabled","tage",""],
    ["bpu","ittage","branchPred.ittage","enabled","ittage",""],
    ["bpu","mgsc","branchPred.mgsc","enabled","mgsc",""],
    ["bpu","ras","branchPred.ras","enabled","ras",""],
    ["mmu","itb","mmu.itb","size","ITB 容量","项"],
    ["mmu","itb","mmu.itb","enable_l1_direct_compression","一级翻译压缩",""],
    ["mmu","dtb","mmu.dtb","size","DTB 容量","项"],
    ["mmu","dtb","mmu.dtb","enable_l1_direct_compression","一级翻译压缩",""],
    ["mmu","shared","mmu.l2_shared","l2tlb_l0_size","共享 L2 · L0","行 × 8 项"],
    ["mmu","shared","mmu.l2_shared","l2tlb_l1_size","共享 L2 · L1","行 × 8 项"],
    ["mmu","shared","mmu.l2_shared","l2tlb_l2_size","共享 L2 · L2","项"],
    ["mmu","shared","mmu.l2_shared","l2tlb_l3_size","共享 L2 · L3","项"],
    ["mmu","shared","mmu.l2_shared","l2tlb_sp_size","共享 L2 · SP","项"],
    ["icache","tag","icache","size","容量","B"],
    ["icache","tag","icache","assoc","组相联度","路"],
    ["icache","tag","icache","replacement_policy","替换策略",""],
    ["icache","tag","icache","prefetcher","预取策略",""],
    ["dcache","tags","dcache","size","容量","B"],
    ["dcache","tags","dcache","assoc","组相联度","路"],
    ["dcache","tags","dcache","replacement_policy","替换策略",""],
    ["dcache","tags","dcache","prefetcher","预取策略",""],
    ["l2","inner","slice","size","容量","B"],
    ["l2","inner","slice","assoc","组相联度","路"],
    ["l2","inner","slice","replacement_policy","替换策略",""],
    ["l2","inner","slice","prefetcher","预取策略",""],
    ["llc","tags","l3","size","容量","B"],
    ["llc","tags","l3","assoc","组相联度","路"],
    ["llc","tags","l3","replacement_policy","替换策略",""],
    ["llc","tags","l3","prefetcher","预取策略",""],
    ["l2","route","wrapper","prefetcher","Wrapper 预取策略",""],
    ["l2","route","wrapper","num_slices","切片数量","片"],
    ["mmu","iwalk","mmu.itb.walker","ptw_miss_queue_size","指令 PTW 等待队列","项"],
    ["mmu","dwalk","mmu.dtb.walker","ptw_miss_queue_size","数据 PTW 等待队列","项"],
    ["decode","input","cpu","fetchToDecodeDelay","取指至译码延迟","周期"],
    ["llc","miss","l3","num_slices","逻辑切片","片"],
    ["fabric","route","membus","width","端口宽度","B/周期"],
    ["mem","backend","mem_ctrls","configFile","DRAM 时序文件",""]
  ].map(([module,node,owner,key,label,unit])=>({module,node,owner,key,label,unit}));
  function load(data) {
    if(!Array.isArray(data.nodes))throw Error('配置缺少实例对象');
    const objects=new Map();
    for(const n of data.nodes){
      if(typeof n.id!=='string'||!n.fields||objects.has(n.id))throw Error('实例路径无效或重复');
      objects.set(n.id,n.fields);
    }
    const cores=[...objects].filter(([,f])=>/O3CPU|DerivO3/.test(f.type)).map(([p])=>p).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
    if(!cores.length)throw Error('未找到可映射至昆明湖详情的 O3 CPU 实例');
    return {objects,cores};
  }
  function context(profile,core){
    const system=core.slice(0,core.lastIndexOf('.')), objects=profile?.objects;
    const cpuSlot=Number(core.match(/(\d+)$/)?.[1]||0);
    function vector(name,all=false){
      const base=system+'.'+name;
      const paths=[...(objects?.keys()||[])].filter(p=>p.startsWith(base)&&/^\d*$/.test(p.slice(base.length)));
      return all?paths:paths.filter(p=>Number(p.slice(base.length)||0)===cpuSlot);
    }
    function owners(owner){
      if(owner==='cpu')return [core];
      if(owner==='l3'||owner==='membus')return [system+'.'+owner];
      if(owner==='mem_ctrls')return vector(owner,true);
      if(owner==='wrapper')return vector('l2_wrappers');
      if(owner==='slice'){
        const wrappers=vector('l2_wrappers');
        const slices=[...(objects?.keys()||[])].filter(p=>wrappers.some(w=>p.startsWith(w+'.')&&/^slices\d*\.inner_cache$/.test(p.slice(w.length+1))));
        return slices.length?slices:vector('l2_caches');
      }
      return [core+'.'+owner];
    }
    function rows(module){
      const result=specs.filter(s=>s.module===module).flatMap(s=>{
        let paths=owners(s.owner);
        if(!paths.length)paths=[null];
        return paths.map(path=>{
          const f=objects?.get(path), ref=f?.[s.key], child=objects?.get(path+'.'+s.key);
          const extracted=sourceParameters[s.owner+'.'+s.key];
          let value=profile?ref:extracted?.value, origin=path?path+'.'+s.key:s.owner+'.'+s.key;
          if(profile&&['replacement_policy','prefetcher'].includes(s.key)){
            const target=objects.get(ref)||child;
            if(target){value=target.type;origin=(objects.has(ref)?ref:path+'.'+s.key)+'.type'}
          }
          const missing=value===undefined||value===null||value==='';
          const scope=s.owner==='slice'?(path?.includes('l2_caches')?'每核 L2':'每切片'):s.owner==='wrapper'?'每核 L2':s.owner==='l3'?'共享 L3 总量':['mem_ctrls','membus'].includes(s.owner)?'系统实例':'每核';
          return {...s,value:missing?null:value,origin:profile?origin:extracted?.path,path:extracted?.path,scope};
        });
      });
      if(module==='l2'){
        const slices=result.filter(r=>r.key==='size'&&r.scope==='每切片');
        const count=result.find(r=>r.key==='num_slices');
        if(slices.length){
          const known=slices.length===Number(count.value)&&slices.every(r=>r.value!==null&&/^\d+$/.test(r.value));
          result.push({module,node:'route',owner:'wrapper',key:'size',label:'各片容量合计',unit:'B',
            value:profile?(known?slices.reduce((sum,r)=>sum+Number(r.value),0):null):sourceParameters['wrapper.size']?.value??null,
            scope:'每核 L2',origin:profile?slices.map(r=>r.origin).join(' + '):sourceParameters['wrapper.size']?.path,path:sourceParameters['wrapper.size']?.path});
        }
      }
      return result;
    }
    return {rows,owners};
  }
  function format(row){
    if(row.value==null)return '未提供';
    const v=String(row.value);
    if(/^true$/i.test(v))return '启用';
    if(/^false$/i.test(v))return '关闭';
    if(/^null$/i.test(v))return '无';
    if(row.unit==='B'&&/^\d+$/.test(v)){
      const n=Number(v);
      if(n&&n%1048576===0)return (n/1048576)+' MiB';
      if(n&&n%1024===0)return (n/1024)+' KiB';
    }
    return [v,row.unit].filter(Boolean).join(' ');
  }
  return {load,context,format};
})();
