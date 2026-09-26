const path = require('node:path');
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const runtime = fs.readFileSync(path.resolve(__dirname, '..', '../life_slimming/public/js/portal_config.js'),'utf8');
const config = fs.readFileSync(path.resolve(__dirname, '..', 'src/api/config.js'),'utf8').replace(/export /g,'');
const client = fs.readFileSync(path.resolve(__dirname, '..', 'src/api/http.js'),'utf8').replace(/^import .*;\n/,'').replace(/export /g,'');
test('shared API client uses configured domain, credentials and request data', async () => {
 const calls=[];
 const context={window:{},fetch:async (...args)=>{calls.push(args);return {ok:true,json:async()=>({message:'ok'})};}};
 vm.createContext(context);
 vm.runInContext(runtime.replace('apiBase: ""','apiBase: "https://api.example.test/"')+config+client+';globalThis.request = request;',context);
 await context.request('login',{args:{usr:'fixture'},csrfToken:'test-token'});
 assert.equal(calls[0][0],'https://api.example.test/api/method/login');
 assert.equal(calls[0][1].credentials,'include');
 assert.equal(calls[0][1].headers['X-Frappe-CSRF-Token'],'test-token');
 assert.equal(calls[0][1].body,'{"usr":"fixture"}');
});
test('default configuration keeps APIs on the current site',()=>{
 const context={window:{}};vm.createContext(context);vm.runInContext(runtime+config,context);
 assert.equal(context.apiUrl('/api/method/login'),'/api/method/login');
 assert.equal(context.apiCredentials(),'same-origin');
});
