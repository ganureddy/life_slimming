const path = require('node:path');
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
test('development serves the shared runtime config without a backend request', async () => {
  const {default: config} = await import('../vite.config.js');
  const plugin = config({command:'serve'}).plugins.find(p=>p.name==='life-portal-runtime-config');
  const [tag] = plugin.transformIndexHtml.handler();
  assert.equal(tag.attrs.src,'/life_portal/portal_config.js');
  assert.equal(plugin.transformIndexHtml.order,'post');
  let handler; plugin.configureServer({middlewares:{use(fn){handler=fn;}}});
  for (const url of [tag.attrs.src, '/portal_config.js?cache=1']) {
    const headers={}; let code;
    handler({url},{setHeader(k,v){headers[k]=v;},end(body){code=body;}},()=>assert.fail('Config was not served'));
    assert.equal(headers['Cache-Control'],'no-store');
    const context={window:{}};vm.runInNewContext(code,context);
    assert.equal(context.window.lifePortalConfig.apiBase,'');
    assert.equal(context.window.lifePortalNetwork.url('/api/method/login'),'/api/method/login');
  }
  let next=false;handler({url:'/other'}, {},()=>{next=true;});assert(next);
});
test('production loads config from the Frappe asset path before the app',()=>{
 const html=fs.readFileSync(path.resolve(__dirname, '..', '../life_slimming/www/life_portal.html'),'utf8');
 assert(html.includes('src="/assets/life_slimming/js/portal_config.js"'));
 assert(html.indexOf('portal_config.js') < html.indexOf('type="module"'));
 assert(!html.includes('/life_portal/assets/life_slimming'));
});
