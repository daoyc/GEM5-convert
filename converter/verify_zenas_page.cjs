// Run against the generated page, including when it is the only file available.
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
const fs = require('node:fs');
const fixtures = fs.existsSync(path.join(__dirname,'test-config.json')) ? __dirname : path.resolve(__dirname,'../../converter');

async function verify() {
  const url = pathToFileURL(path.resolve(process.argv[2] || 'GEM5.html')).href;
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH});
  const errors = [];
  try {
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    await page.route('**/*', route => {
      if (route.request().url() === url) return route.continue();
      errors.push('External dependency: '+route.request().url());
      return route.abort();
    });
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url);
    await page.waitForSelector('#map .node');
    const result = await page.evaluate(() => {
      const get = id => document.getElementById(id);
      const profile = JSON.parse(get('embedded').textContent).view;
      let scenes=0, events=0;
      const check=(v,msg)=>{if(!v)throw Error(msg)};
      const select=(id,val)=>{get(id).value=val;get(id).dispatchEvent(new Event('change'))};
      for(const graph of [profile,...profile.modules]){
        select('view',graph.id);
        const parts=Array.from(get('map').querySelectorAll('.node'));
        if(graph.parts){
          check(graph.parts.filter(p=>p.role==='internal').length>=2,graph.id+' missing subcomponents');
          check(graph.parts.filter(p=>p.role==='internal').every(p=>parts.some(node=>node.dataset.node===p.id)),graph.id+' missing card');
        }
        if(graph.parts){
          const part=graph.parts.find(p=>p.role==='internal'&&p.evidence?.line);
          const node=parts.find(node=>node.dataset.node===part.id);
          node.dispatchEvent(new Event('click'));
          check(get('props').innerText.includes(part.evidence.file+':'+part.evidence.line),graph.id+' node source inspection');
          const edge=graph.internalEdges.find(e=>e.evidence?.line);
          const wire=Array.from(get('map').querySelectorAll('.edge')).find(g=>g.dataset.edge===edge.id);
          wire.dispatchEvent(new Event('click'));
          const loc=edge.evidence.file+':'+edge.evidence.line;
          const summary=Array.from(get('props').querySelectorAll('summary')).find(el=>el.textContent===loc);
          check(summary,graph.id+' edge source inspection');summary.click();
          check(summary.parentNode.querySelector('pre').textContent.trim().length>loc.length,graph.id+' missing source excerpt');
        }
        const options=Array.from(get('scenario').options);
        check(options.length>0,graph.id+' has no scenarios');
        check(options.length===graph.scenarios.filter(s=>s.sourceEnabled!==false).length,graph.id+' scenario coverage mismatch');
        for(const option of options){
          select('scenario',option.value); scenes++;
          const buttons=Array.from(get('sequence').querySelectorAll('button'));
          check(buttons.length>0,graph.id+' empty event list');
          for(const [idx,button] of buttons.entries()){
            button.click();
            const hot=get('map').querySelectorAll('.edge.active');
            check(hot.length===1,graph.id+' '+option.text+' event '+idx+' needs one active edge');
            const expected=graph.scenarios.find(s=>s.name===option.text)?.steps[idx];
            check(expected && expected.edgeId===hot[0].dataset.edge &&
                  expected.a===hot[0].dataset.from && expected.b===hot[0].dataset.to,
                  graph.id+' event identity or direction mismatch');
            const animation=hot[0].querySelector('animateMotion');
            check(animation,graph.id+' particle missing');
            const wire=hot[0].querySelector('.wire');
            const motion=document.createElementNS('http://www.w3.org/2000/svg','path');
            motion.setAttribute('d',animation.getAttribute('path'));
            const shift=animation.parentElement.parentElement.transform.baseVal.consolidate()?.matrix;
            for(const fraction of [0,.25,.5,.75,1]){
              const a=wire.getPointAtLength(wire.getTotalLength()*fraction), b=motion.getPointAtLength(motion.getTotalLength()*fraction);
              check(Math.hypot(a.x-b.x-(shift?.e||0),a.y-b.y-(shift?.f||0))<.1,graph.id+' particle/shaft mismatch');
            }
            check(get('map').querySelector('[data-stream="send"]')?.dataset.node===expected.a, graph.id+' sender mismatch');
            check(get('map').querySelector('[data-stream="receive"]')?.dataset.node===expected.b, graph.id+' receiver mismatch');
            check(button.querySelector('.step-route')?.textContent.includes('→'),graph.id+' missing endpoint labels');
            check(button.classList.contains('active')&&get('sequence').querySelectorAll('.active').length===1,graph.id+' list out of sync');
            for(const side of ['from','to'])check(parts.some(n=>n.dataset.node===hot[0].dataset[side]),graph.id+' missing '+side);
            events++;
          }
        }
      }
      select('view',profile.id);
      return {modules:profile.modules.length,scenes,events};
    });
    const logical=await page.evaluate(()=>{
      const v=JSON.parse(document.querySelector('#embedded').textContent).view;
      const e=v.edges.find(e=>!v.edges.some(r=>r.a===e.b&&r.b===e.a)&&v.edges.filter(r=>r.a===e.a&&r.b===e.b).length===1);
      return {viewId:v.id,a:e.a,b:e.b,id:e.id};
    });
    const upload=(name,step)=>page.setInputFiles('#trace',{name,mimeType:'application/json',
      buffer:Buffer.from(JSON.stringify({name,viewId:logical.viewId,steps:[step]}))});
    await upload('unique.json',{a:logical.a,b:logical.b,type:'request',text:'unique'});
    await page.waitForFunction(()=>document.querySelector('#scene').textContent.includes('unique.json'));
    assert.equal(await page.locator('#map .edge.active').getAttribute('data-edge'),logical.id);
    await upload('wrong-dir.json',{a:logical.b,b:logical.a,type:'reply',text:'wrong direction'});
    await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('无法匹配'));
    assert.equal(await page.locator('#map .edge.active').getAttribute('data-edge'),logical.id);
    await page.selectOption('#scenario',{index:0});
    const node=page.locator('#map [data-node="issue"]');
    await node.hover();
    assert.equal(await node.getAttribute('data-relation'),'center');
    assert.ok(await page.locator('#map .edge[data-relation=up]').count()>0);
    assert.ok(await page.locator('#map .edge[data-relation=down]').count()>0);
    assert.ok(await page.locator('#map .node[data-relation=other]').count()>0);
    await page.locator('#title').hover();
    assert.equal(await page.locator('#map [data-relation=center]').count(),0);
    await page.locator('#sequence button').first().click();
    const dot=page.locator('#map .edge.active .flow-dot');
    const point=()=>dot.evaluate(el=>{const r=el.getBoundingClientRect();return [r.x,r.y]});
    const before=await point();
    await page.waitForFunction(([x,y])=>{
      const r=document.querySelector('#map .edge.active .flow-dot').getBoundingClientRect();
      return Math.hypot(r.x-x,r.y-y)>6;
    },before);
    await page.locator('#play').click();
    await page.waitForFunction(()=>!document.querySelector('#sequence button').classList.contains('active'));
    await page.locator('#play').click();
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'page overflows on mobile');
    await page.setViewportSize({width:1280,height:900});
    await page.locator('#config').setInputFiles(path.join(fixtures,'test-config.json'));
    await page.locator('#trace').setInputFiles(path.join(fixtures,'test-trace.json'));
    await page.waitForFunction(()=>document.getElementById('scene').textContent.includes('test-trace.json'));
    assert.equal(await page.locator('#map .edge.active .flow-dot').count(),1);
    await page.locator('#sequence button').nth(1).click();
    assert.match(await page.locator('#event').innerText(),/9007199254740993/);
    await page.locator('#trace').setInputFiles(path.join(fixtures,'test-trace-ambiguous.json'));
    await page.waitForFunction(()=>document.getElementById('message').textContent.includes('歧义'));
    assert.equal(await page.locator('#sequence button').count(),2);
    const beforeBad=await page.locator('#event').textContent();
    await page.setInputFiles('#trace',{name:'missing.json',mimeType:'application/json',
      buffer:Buffer.from(JSON.stringify({name:'missing',steps:[{edgeId:'no-such-edge',a:'absent-a',b:'absent-b',type:'request',text:'miss'}]}))});
    await page.waitForFunction(()=>document.getElementById('message').textContent.includes('no-such-edge'));
    assert.equal(await page.locator('#event').textContent(),beforeBad);
    assert.match(await page.locator('#message').innerText(),/absent-a.*absent-b/);
    const legacy={format:'core-atlas/1',name:'Legacy import',
      nodes:[{id:'ExampleCPU',name:'ExampleCPU',fields:{}},{id:'ParentCPU',name:'ParentCPU',fields:{}}],
      edges:[['ExampleCPU','ParentCPU','继承']]};
    await page.setInputFiles('#file',{name:'legacy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(legacy))});
    await page.waitForFunction(()=>document.querySelector('#model').selectedOptions[0].textContent==='Legacy import');
    await page.fill('#search','ParentCPU');
    await page.selectOption('#object','ParentCPU');
    assert.equal(await page.locator('#title').innerText(),'ParentCPU');
    assert.match(await page.locator('#counts').innerText(),/1 条直接关系/);
    assert.deepEqual(errors,[]);
    console.log('PASS',JSON.stringify(result),'all event arrows and motion paths, real particle movement, hover, play, mobile width, offline');
  } finally {await browser.close()}
}
verify().catch(err=>{console.error(err);process.exitCode=1});
