import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createEmployeeAnalytics} from '../src/lib/employee-analytics.js';
import {createTaskDomain} from '../src/lib/task-domain.js';
import {createClusterData} from '../src/lib/cluster-data.js';
const invoice={invoice:'INV-1',invoice_date:'2026-10-25',branch:'A',customer:'C-1',referring_employee:'Priya',referring_employee_id:'E-1',incentive_employee:'Arun',incentive_employee_id:'E-2',referring_employee_share:600,incentive_employee_share:400,paid_amount:1050,paid_amount_without_tax:1000,gst_amount:50,grand_total:2100,outstanding_amount:1050,therapy_details:[{category:'Slimming',group:'Body',type:'Cryo',amount:750},{category:'Skin',group:'Face',type:'Facial',amount:250}]};
const filters={branch:'',emp:[],role:[],sharing:[],category:[],group:[],type:[],booking:[],mop:[],paidMin:null,paidMax:null,outMin:null,outMax:null,onlyOut:false,treat:false};
test('employee Vue calculations conserve allocations and treatment-share weighting without mutating records',()=>{
 const S={raw:[],alias:{},empInfo:{},basis:'full'},calc=createEmployeeAnalytics(S);S.raw=[calc.normalize(invoice)];calc.buildAlias(calc.buildCredits(S.raw));const before=JSON.stringify(S.raw);
 let V=calc.compute(filters);assert.equal(calc.totals(V).ex,1000);assert.equal(V.credits.reduce((n,c)=>n+c.paid,0),1050);assert.equal(calc.aggEmployees(V.credits).length,2);assert.equal(calc.aggTree(V.credits,V.f).total,1000);
 S.basis='share';V=calc.compute({...filters,category:['Skin'],treat:true});assert.equal(calc.totals(V).ex,250);assert.equal(V.credits.reduce((n,c)=>n+c.gst,0),12.5);
 assert.equal(calc.compute({...filters,category:['Skin'],group:['Body'],treat:true}).invs.length,0);assert.equal(JSON.stringify(S.raw),before);
});
test('employee same identity combines both credit roles and only selected role share is counted',()=>{
 const S={raw:[],alias:{},empInfo:{},basis:'full'},calc=createEmployeeAnalytics(S);S.raw=[calc.normalize({...invoice,incentive_employee_id:' e-1 ',incentive_employee:'Priya'})];calc.buildAlias(calc.buildCredits(S.raw));const V=calc.compute({...filters,role:['inc']});assert.equal(V.credits.length,1);assert.equal(calc.totals(V).ex,400);assert.equal(calc.aggEmployees(V.credits)[0].inc,400);
});
function tasks(){const documents=new Map(),writes=[];const S={cfg:{},people:[{user:'a',name:'A',login:true,branch:'One',dept:'Services',desig:'Therapist'},{user:'b',name:'B',login:true,branch:'Two',dept:'Services',desig:'Therapist'}],byUser:{},me:{},tasks:[],tickets:[],files:{},tfiles:{},tab:{task:'my',ticket:'tmy'},phoneUntil:0};S.people.forEach(p=>S.byUser[p.user]=p);const API={get:async(dt,id)=>structuredClone(documents.get(id)),save:async(dt,id,fields)=>{writes.push({dt,id,fields});Object.assign(documents.get(id),structuredClone(fields));}};const d=createTaskDomain(S,API,()=>{});S.cfg=d.defaultCfg();S.me=d.setMe('a','A');d.resetForm();return {S,d,documents,writes};}
test('tasks Vue preserves task metadata through saves, enforces own visibility and maintains review completion',async()=>{
 const {S,d,documents,writes}=tasks();Object.assign(S.form,{title:'Test',details:'Complete treatment report',cat:'Services',pri:'HI',report:{type:'COMPLETION'},sel:['a']});
 const task=d.newBase(S.form,'a',{}),raw={...d.denormBase(task),name:'TD-1',allocated_to:'a',assigned_by:'b',owner:'b',creation:'2026-10-25 10:00:00'};documents.set(raw.name,raw);S.tasks=[d.enrich(d.base(raw)),d.enrich(d.base({...raw,name:'HIDDEN',allocated_to:'b',assigned_by:'b'}))];S.cfg.roles.Employee.scope='own';assert.deepEqual(d.visible().map(t=>t.id),['TD-1']);
 await d.persist('TD-1',t=>{t.status='Review Pending';t.progress=100;d.addUpd(t,'Completion','Done');},'Saved');assert.equal(S.tasks[0].status,'Review Pending');assert.equal(d.base(documents.get('TD-1')).updates.at(-1).text,'Done');assert(writes.some(w=>w.fields.description?.includes('LIFE_TASK_META')));
});
test('group task per-member completion remains distinct and queue order failures propagate',async()=>{
 const {S,d,documents}=tasks();const task=d.newBase(S.form,'a',{title:'Group',grp:{id:'G1',members:['a','b'],leader:'a',response:'individual',mirrors:{}},meta:{mq:{a:1,b:1},mstate:{}}});const raw={...d.denormBase(task),name:'MASTER',allocated_to:'a',assigned_by:'a',creation:'2026-10-25 10:00:00'};documents.set('MASTER',raw);S.tasks=d.explode(d.base(raw));
 await d.persist('MASTER::a',t=>{t.status='Completed';t.progress=100;t.completedOn=d.nowLocal();},'Completed');assert.equal(d.findTask('MASTER::a').status,'Completed');assert.equal(d.findTask('MASTER::b').status,'Open');assert.equal(d.base(documents.get('MASTER')).status,'In Progress');
 const broken=createTaskDomain(S,{get:async()=>{throw Error('Permission denied');},save:async()=>{throw Error('Permission denied');}},()=>{});await assert.rejects(()=>broken.writeGroupMq('MASTER',{a:2}),/Permission denied/);
});
test('cluster data retains distinct recovery commitments and verified paid-invoice ranking',()=>{
 const data=createClusterData({rows:[]},{});assert.deepEqual(data.stats([{due:100,st:'PARTIAL',colAmt:20,cmtAmt:30},{due:50,st:'NOTCOLL'},{due:70,st:'COMMITTED',cmtAmt:40}]),{gross:220,collected:20,committed:70,writeoff:50,real:150});assert.equal(data.paid({grand_total:100,is_return:0,outstanding_amount:0}),true);assert.equal(data.paid({grand_total:100,is_return:0,outstanding_amount:1}),false);assert.equal(data.paid({grand_total:100,is_return:1,outstanding_amount:0}),false);
});
test('all three page entry points use reactive composables and Vue components, with no controller renderer',()=>{
 for(const name of ['TaskManager','EmployeeSaleMaster','ClusterDashboard']){const source=fs.readFileSync(new URL('../src/pages/'+name+'Page.vue',import.meta.url),'utf8');assert(!/controllers\/|createDomPageRuntime|mountTask|mountEmployee|mountCluster|v-pre|v-html|innerHTML|<iframe|new Function|eval\(/.test(source),name);assert(/NativeTable|EmployeeReportTable/.test(source));assert(/useTaskManager|useEmployeeAnalytics|useClusterDashboard/.test(source));}
 for(const name of ['task-domain','employee-analytics','cluster-data']){const source=fs.readFileSync(new URL('../src/lib/'+name+'.js',import.meta.url),'utf8');assert(!/innerHTML|outerHTML|querySelector|createElement|document\./.test(source),name);}
});
