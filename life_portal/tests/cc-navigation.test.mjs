import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ccTabs,ccRoute,ccPagePath,ccViewOfRoute,isCcRoute} from '../src/lib/cc-navigation.js';
test('every CRM page has a distinct path and preserves filter parameters',()=>{
  const paths=ccTabs.map(tab=>ccPagePath(tab.view));
  assert.equal(new Set(paths).size,ccTabs.length);
  assert.equal(ccPagePath('followup'),'follow-up');
  assert.equal(ccPagePath('distribution'),'distribution');
  const query={view:'create',from:'2026-11-01',to:'2026-11-11',mode:'posting'};
  assert.deepEqual(ccRoute('create',query),{name:'cc-leads-create',query:{from:'2026-11-01',to:'2026-11-11',mode:'posting'}});
  assert.equal(query.view,'create');
});
test('lead details use their own route parameter and child pages share CRM access',()=>{
  assert.deepEqual(ccRoute('followup',{lead:'CRM-LEAD-1',from:'2026-11-01'}),{name:'cc-leads-followup',params:{leadId:'CRM-LEAD-1'},query:{from:'2026-11-01'}});
  const route={name:'cc-leads-distribution',meta:{accessModule:'leads',ccView:'distribution'},query:{}};
  assert.equal(isCcRoute(route),true);assert.equal(ccViewOfRoute(route),'distribution');
  assert.equal(isCcRoute({name:'home',meta:{}}),false);
});
