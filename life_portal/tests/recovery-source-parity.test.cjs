const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const postcss=require('../node_modules/postcss');
const root=path.join(__dirname,'..');
const original=JSON.parse(fs.readFileSync(path.join(root,'../life_slimming/portal_pages/pending-balances-updates.json')));
const normalize=value=>value.replace(/\s+/g,' ').replace(/\s*([,>+~])\s*/g,'$1').trim();
function rules(css,source){const result=new Set();postcss.parse(css).walkRules(rule=>{
 if(rule.selector==='.navbar')return;
 const keyframe=rule.parent.type==='atrule'&&/keyframes$/.test(rule.parent.name);
 const selector=normalize(rule.selectors.map(value=>{if(value.startsWith(':deep('))value=value.slice(6,-1);if(source&&!keyframe&&!value.includes('#pdr-app'))value='#pdr-app '+value;return value;}).join(','));
 const parents=[];for(let parent=rule.parent;parent;parent=parent.parent)if(parent.type==='atrule')parents.unshift(parent.name+':'+normalize(parent.params));
 const declarations=rule.nodes.filter(node=>node.type==='decl').map(node=>node.prop+':'+node.value.replace(/\s+/g,'')+(node.important&&node.prop!=='font-size'?'!important':'')).join(';');
 result.add(parents.join('/')+'|'+selector+'|'+declarations);
});return result;}
test('Pending Balances retains every original page style declaration with module scoping',()=>{const native=rules(fs.readFileSync(path.join(root,'src/styles/recovery-source.css'),'utf8'),false);assert.deepEqual([...rules(original.css,true)].filter(rule=>!native.has(rule)),[]);});
test('Pending Balances owns the original nine sections and full manager register in Vue',()=>{const page=fs.readFileSync(path.join(root,'src/pages/PendingBalancesPage.vue'),'utf8');for(const id of ['pSchedule','pEmp','pCollection','pOverview','pFilter','pMain','pClean','pBr','pFlow'])assert(page.includes('id="'+id+'"'),id);const headers=[...page.matchAll(/data-sort-key="([^"]+)"/g)].map(match=>match[1]);assert.deepEqual(headers,['branch','client','emp','inv','invAmt','paid','due','nextDue','st','colAmt','colDate','mode','cmtAmt','cmtDate','reasonRemark']);assert(!/v-html|innerHTML|onclick=|onchange=|PDR\./.test(page));assert(page.includes('RecoveryClientCell'));});
