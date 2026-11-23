// node verify_xs_page.cjs [generated HTML]. Requires Playwright and Chromium.
// Set NODE_PATH for an external Playwright installation, CHROME_PATH for an installed browser.
const fs = require('node:fs/promises');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

async function layoutSnapshot(page) {
  return page.locator('#diagram').evaluate(root => ({
    bounds:root.getAttribute('viewBox'),
    nodes:Array.from(root.querySelectorAll('.node'),n=>[n.dataset.node,n.getAttribute('transform')]),
    edges:Array.from(root.querySelectorAll('.edge'),e=>[e.dataset.from,e.dataset.to,e.querySelector('.wire').getAttribute('d')]),
    scenarios:Array.from(document.querySelector('#scenario').options,o=>o.textContent),
  }));
}

async function verify(browser, url, reference) {
  const context = await browser.newContext({viewport: {width:1440, height:960}});
  const page = await context.newPage();
  const errors = [], dependencies = [];
  page.on('pageerror', err => errors.push(err.message));
  // The HTML is the only file in the temporary directory and the only served URL.
  // Download controls may use data: and blob: URLs. No other resource is required.
  await context.route('**/*', async route => {
    const address = route.request().url();
    if (address === url || /^(data|blob):/.test(address)) return route.continue();
    dependencies.push(address);
    return route.abort();
  });
  try {
    await page.goto(url);
    await page.waitForSelector('#diagram .node');
    if (reference) assert.deepEqual(await layoutSnapshot(page), reference.get('overview'));
    assert.equal(await page.locator('#diagram .node').count(), 16);
    assert.equal(await page.locator('#diagram .edge').count(), 20);
    assert.equal(await page.locator('#scenario option').count(), 5);
    await page.click('#plus');
    assert.match(await page.locator('#scale').innerText(), /115/);
    await page.click('#scale');
    await page.click('#objectsButton');
    const sourceBrowser = page.frameLocator('#objectsFrame');
    await sourceBrowser.locator('#search').fill('RiscvO3CPU');
    const result = sourceBrowser.locator('#object option').filter({hasText:'RiscvO3CPU'}).first();
    await sourceBrowser.locator('#object').selectOption(await result.getAttribute('value'));
    assert.match(await sourceBrowser.locator('#title').textContent(),/RiscvO3CPU/);
    await page.click('#closeObjects');
    const ids = ['bpu','ftq','ifu','icache','decode','rename','dispatch','iew',
      'commit','lsu','mmu','dcache','l2','llc','fabric','mem'];
    for (const id of ids) {
      await page.click('#diagram [data-node="'+id+'"]');
      await page.waitForFunction(value => document.querySelector('#deep').value === value, id);
      if (reference) assert.deepEqual(await layoutSnapshot(page), reference.get(id),id);
      assert.ok(await page.locator('#diagram .node').count() >= 4, id);
      assert.ok(await page.locator('#scenario option').count() > 0, id);
      if (id === 'mmu' || id === 'icache') {
        const title = await page.locator('#diagram .edge title').first().textContent();
        // The shaft follows an orthogonal route. Its midpoint is not necessarily on the path.
        await page.locator('#diagram .edge').first().dispatchEvent('click');
        assert.equal(await page.locator('#info h2').textContent(), title);
        await page.click('#info a, #info button');
        await page.waitForSelector('#sourceDialog .selected');
        assert.ok((await page.locator('#sourceDialog .selected').innerText()).trim());
        await page.click('#closeSource');
        assert.ok(await page.locator('#paramRows').innerText(), id);
      }
      await page.click('#home');
      await page.waitForFunction(() => !document.querySelector('#deep').value);
    }
    const file = (data, name) => ({
      name, mimeType:'application/json', buffer:Buffer.from(JSON.stringify(data)),
    });
    const trace = {name:'取指翻译校验',graph:'overview',steps:[
      {a:'ifu',b:'mmu',type:'request',text:'发起翻译',tick:'9007199254740993'},
      {a:'mmu',b:'ifu',type:'response',text:'返回物理地址',tick:'9007199254740993'},
    ]};
    await page.setInputFiles('#upload', file(trace, 'translation.json'));
    await page.waitForFunction(() => document.querySelector('#scenario').value === 'imported');
    await page.click('#next');
    const active = await page.locator('#log .active').textContent();
    assert.ok(active.includes('返回物理地址') && active.includes('9007199254740993'), active);
    assert.equal(await page.locator('#diagram .edge[data-from=mmu][data-to=ifu] .flow-dot').count(),1);
    const invalid = {...trace,steps:[{...trace.steps[0],a:'missing-source'}]};
    await page.setInputFiles('#upload', file(invalid, 'invalid.json'));
    await page.waitForFunction(() => document.querySelector('#msg').textContent.includes('missing-source'));
    assert.equal(await page.locator('#log .active').textContent(),active);
    assert.equal(await page.locator('#scenario').inputValue(),'imported');
    await page.setInputFiles('#profileFiles',path.join(__dirname,'examples','variant.json'));
    await page.waitForFunction(() => document.querySelector('#core').options.length === 2);
    await page.selectOption('#deep','commit');
    const rob = page.locator('#paramRows > div').filter({hasText:'ROB 容量'}).locator('strong');
    assert.match(await rob.innerText(),/256/);
    await page.selectOption('#core','system.cpu1');
    assert.match(await rob.innerText(),/192/);
    await page.selectOption('#profile','default');
    assert.match(await rob.innerText(),/352/);
    assert.deepEqual(errors,[]);
    assert.deepEqual(dependencies,[]);
    console.log(url.split(':', 1)[0]+' passed: overview, 16 drill-downs, source inspection and trace playback');
  } finally {
    await context.close();
  }
}

async function main() {
  const input = process.argv[2] || path.join(__dirname, 'GEM5.html');
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'xs-page-'));
  const page = path.join(directory,'isolated.html');
  const html = await fs.readFile(input);
  await fs.writeFile(page, html);
  const server = http.createServer((req,res) => {
    if(req.url !== '/isolated.html') {res.writeHead(404).end();return}
    res.writeHead(200, {'content-type':'text/html; charset=utf-8'}).end(html);
  });
  let browser;
  try {
    browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
    let reference;
    if(process.env.XS_REFERENCE_URL) {
      reference = new Map();
      const original = await browser.newPage({viewport:{width:1440,height:960}});
      await original.goto(process.env.XS_REFERENCE_URL);
      await original.waitForSelector('#diagram .node');
      reference.set('overview', await layoutSnapshot(original));
      const ids = await original.locator('#deep option').evaluateAll(options => options.map(o=>o.value).filter(Boolean));
      for(const id of ids) {
        await original.selectOption('#deep',id);
        await original.waitForFunction(id=>location.hash==='#'+id && document.querySelector('#heading').textContent.indexOf('架构总览')===-1,id);
        reference.set(id,await layoutSnapshot(original));
      }
      await original.close();
    }
    await verify(browser,pathToFileURL(page).href,reference);
    await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
    await verify(browser,'http://127.0.0.1:'+server.address().port+'/isolated.html');
  } finally {
    if(browser) await browser.close();
    if(server.listening) await new Promise(resolve => server.close(resolve));
    await fs.rm(directory,{recursive:true,force:true});
  }
}
main().catch(error => {console.error(error);process.exitCode=1});




