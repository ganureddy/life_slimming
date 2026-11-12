import test from 'node:test';import assert from 'node:assert/strict';import {tabAllowed} from '../src/lib/portal-tab-access.js';
const tabs={ccvisit:[{id:'visits'},{id:'agents'},{id:'convox',parent:'agents'},{id:'standalone'}]};
test('existing role configurations inherit tab access',()=>{assert.equal(tabAllowed(tabs,{groups:'ALL'},'ccvisit','visits'),true);assert.equal(tabAllowed(tabs,{},'ccvisit','unknown'),false);});
test('denied parent tab also denies its subpages; standalone remains independent',()=>{const config={tab_access:{ccvisit:{agents:false,convox:true,standalone:true}}};assert.equal(tabAllowed(tabs,config,'ccvisit','convox'),false);assert.equal(tabAllowed(tabs,config,'ccvisit','standalone'),true);});
