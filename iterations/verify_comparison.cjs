// Offline verification of the published pair and a three-CPU runtime fixture.
const {chromium} = require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const parent=path.resolve(__dirname,'..');
async function main(){
  const files=process.argv.length===4?process.argv.slice(2):['GEM5-1.html','GEM5-2.html'].map(f=>path.join(parent,f));
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH});
  try{
    for(const [i,file] of files.entries()){
      const page=await browser.newPage(), url=pathToFileURL(path.resolve(file)).href;
      const errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/*',route=>route.request().url()===url?route.continue():(errors.push(route.request().url()),route.abort()));
      await page.goto(url);
      await page.selectOption('#view','issue');await page.locator('#coveragePanel summary').first().click();
      await page.setInputFiles('#compareFile',path.resolve(files[1-i]));
      await page.locator('#removeComparison').waitFor({state:'visible'});
      const intRow=page.locator('#coverageRows tr[data-label="整数 IQ"]');
      await intRow.waitFor();
      const text=await intRow.textContent();
      assert.match(text,/192/);assert.match(text,/72/);
      assert.match(await page.locator('#coverageRows').innerText(),/定向|唤醒/);
      await page.selectOption('#view','ifu');
      await page.click('#removeComparison');
      const row=page.locator('#coverageRows tr[data-label="resident window replay"]');
      assert.match(await row.innerText(),i===0?/关闭/:/缺失/);
      const resident=page.locator('#scenario option').filter({hasText:'驻留窗口命中与解码供给'});
      assert.equal(await resident.count(),0);
      await page.setInputFiles('#config',path.join(__dirname,'08-runtime.json'));
      await page.waitForFunction(()=>document.querySelector('#configuration').options.length===2);
      await page.selectOption('#scope','system.cpu0');
      assert.equal(await resident.count(),i===0?1:0);
      if(i===0){
        assert.match(await row.innerText(),/system\.cpu0\.enableFetchResidentWindowReplay = 启用/);
        await page.selectOption('#scenario',await resident.getAttribute('value'));
        const n=await page.locator('#sequence button').count();assert.equal(n,3);
        for(let step=0;step<n;step++){
          await page.locator('#sequence button').nth(step).click();
          const status=await page.evaluate(()=>{
            const edge=document.querySelector('.edge.active'), send=document.querySelector('[data-stream=send]'), recv=document.querySelector('[data-stream=receive]');
            return edge?.dataset.from===send?.dataset.node&&edge?.dataset.to===recv?.dataset.node&&!!edge?.querySelector('animateMotion');
          });assert.ok(status);
        }
      }
      await page.selectOption('#scope','system.cpu1');assert.equal(await resident.count(),0);
      if(i===0)assert.match(await row.innerText(),/system\.cpu1\.enableFetchResidentWindowReplay = 关闭/);
      await page.selectOption('#scope','system.cpu2');assert.equal(await resident.count(),0);
      if(i===0)assert.match(await row.innerText(),/未导出/);
      await page.selectOption('#view','commit');
      await page.selectOption('#scope','system.cpu0');
      assert.match(await page.locator('#coverageRows tr[data-label="ROB 容量"]').innerText(),/320/);
      await page.selectOption('#scope','system.cpu1');
      assert.match(await page.locator('#coverageRows tr[data-label="ROB 容量"]').innerText(),/192/);
      await page.selectOption('#view','l2');
      const size=page.locator('#coverageRows tr[data-label="缓存容量"] td').last();
      assert.equal(await size.innerText(),'system.l2_caches1.size = 2097152');
      await page.selectOption('#scope','system.cpu0');
      assert.equal(await size.innerText(),'system.l2_caches0.size = 1048576');
      await page.selectOption('#scope','system.cpu2');
      assert.equal(await size.innerText(),'未导出');
      await page.selectOption('#scope','');
      assert.deepEqual((await size.innerText()).split('\n'),[
        'system.l2_caches0.size = 1048576','system.l2_caches1.size = 2097152']);
      await page.selectOption('#view','mem');
      const timing=page.locator('#coverageRows tr[data-label="DRAM 时序配置文件"] td').last();
      const channels=['system.mem_ctrls0.configFile = channel0.ini','system.mem_ctrls1.configFile = channel1.ini'];
      assert.deepEqual((await timing.innerText()).split('\n'),channels);
      await page.selectOption('#scope','system.cpu1');
      assert.deepEqual((await timing.innerText()).split('\n'),channels);
      await page.selectOption('#view','commit');
      await page.selectOption('#configuration','source');
      assert.equal(await page.locator('#view').inputValue(),'commit');
      assert.ok(!(await page.locator('#coverageHead').innerText()).includes('运行实例'));
      assert.deepEqual(errors,[]);await page.close();
      console.log(path.basename(file),'OK · offline diff, source/instance switch, conditional replay and selected CPU');
    }
  }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});

