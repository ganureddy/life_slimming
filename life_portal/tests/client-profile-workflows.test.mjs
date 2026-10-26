import {test} from 'node:test';
import assert from 'node:assert/strict';
import {safeFileUrl,loadClientDocuments,loadClientStock,saveClientRemark,linkedClientRecords} from '../src/lib/client-profile-sections.js';
import {normalizeClientMobile,saveClientContact} from '../src/lib/client-contacts.js';
import {ticketActionAllowed} from '../src/lib/task-domain.js';

const bundle=()=>({pid:'P-1',patient:{name:'P-1',patient_name:'Client',customer:'C-1'},plans:[],sessions:[],appts:[],followups:[],lazy:{}});
test('document aggregation deduplicates safe attachments and excludes Sales Invoice files',async()=>{
 const b=bundle();b.patient.image='/files/photo.png';let paymentReads=0;
 const reader={list:async(dt,filters)=>dt==='Payment Entry'?[{name:'PE-1'}]:[{file_url:'/files/photo.png',file_name:'Portrait'},{file_url:'javascript:alert(1)'},{file_url:'/private/files/consent.pdf',file_name:'Consent'}],chunks:async(ids,read)=>read(ids),pool:async(items,read)=>Promise.all(items.map(read)),doc:async()=>{paymentReads++;return{name:'PE-1',custom_payment_proof:'/files/proof.png'};}};
 const files=await loadClientDocuments(reader,b);assert.equal(files.filter(f=>f.url==='/files/photo.png').length,1);assert(files.some(f=>f.catLabel==='✍️ Consent'));assert(files.some(f=>f.catLabel==='🧾 Payment proof'));assert.equal(paymentReads,1);
 for(const url of ['javascript:alert(1)','data:text/html,test','//evil.test/file','/app/patient/P-1','https://user:password@example.test/a'])assert.equal(safeFileUrl(url),'');
 assert.equal(safeFileUrl('/private/files/file.pdf'),'/private/files/file.pdf');
});
test('linked histories scope Patient and Customer links and retain permission failures',async()=>{
 const seen=[];const result=await linkedClientRecords({meta:async dt=>{if(dt==='Denied')throw Object.assign(Error('No permission'),{code:'PermissionError'});return[{fieldname:dt==='PatientLinked'?'patient':'customer',fieldtype:'Link',options:dt==='PatientLinked'?'Patient':'Customer'}];},list:async(dt,filters)=>{seen.push([dt,filters]);return[{name:dt}];}},['PatientLinked','CustomerLinked','Denied'],bundle());
 assert.deepEqual(seen,[['PatientLinked',[['patient','=','P-1']]],['CustomerLinked',[['customer','=','C-1']]]]);assert.equal(result.records.length,2);assert.match(result.warnings[0],/Denied.*No permission/);
});
test('stock combines requests found by ID/name once and groups issued rows by stock entry',async()=>{
 const result=await loadClientStock({list:async()=>[{name:'MR-1'}],pool:async(items,read)=>Promise.all(items.map(read)),doc:async()=>({name:'MR-1',items:[{qty:2}]}),call:async()=>[{stock_entry:'SE-1',qty:1},{stock_entry:'SE-1',qty:2}]},bundle());assert.equal(result.mr.length,1);assert.equal(result.se.length,1);assert.equal(result.se[0].items.length,2);
 await assert.rejects(()=>loadClientStock({list:async()=>{throw Error('Stock denied');},call:async()=>[]},bundle()),/Stock denied/);
});
test('remark writes merge a fresh Patient value, verify storage and report audit failure separately',async()=>{
 const b=bundle();let stored='An existing remark',read=0;const reader={doc:async()=>{read++;return{name:'P-1',custom_remarks:stored};},call:async(method,args)=>{if(method==='frappe.client.set_value'){assert(args.value.startsWith('An existing remark\n'));stored=args.value;return{};}throw Error('Comment permission denied');}};
 const result=await saveClientRemark(reader,b,'[General] New remark');assert.equal(read,2);assert.match(result.patient.custom_remarks,/New remark/);assert.equal(result.warning,'Comment permission denied');
 await assert.rejects(()=>saveClientRemark({doc:async()=>({custom_remarks:'unchanged'}),call:async()=>({})},b,'[General] Unconfirmed'),/did not confirm/);
});
test('contact writes normalize Indian numbers, recheck ownership and preserve current child records',async()=>{
 assert.equal(normalizeClientMobile('+91 98765-43210'),'9876543210');assert.throws(()=>normalizeClientMobile('12345'),/valid 10-digit/);
 const b=bundle(),schema={fields:[{fieldname:'mobile',fieldtype:'Data'}],table:{fieldname:'custom_contact_numbers_',options:'Contact Number'},number:{fieldname:'number'}};let saved;
 const reader={call:async(method,args)=>method==='frappe.client.get_list'?[]:(saved=args.doc),doc:async()=>({name:'P-1',phone:'9123456789',custom_contact_numbers_:[{number:'9000000000',name:'EXISTING'}]})};
 await saveClientContact(reader,b,'9876543210',schema,'','');assert.equal(saved.custom_contact_numbers_.length,2);assert.equal(saved.custom_contact_numbers_[0].name,'EXISTING');
 let wrote=false;await assert.rejects(()=>saveClientContact({call:async(method)=>{if(method==='frappe.client.get_list')return[{name:'OTHER'}];wrote=true;},doc:async()=>({})},b,'9876543210',schema,'',''),/now belongs to another client/);assert.equal(wrote,false);
});
test('ticket role/state action rules match the original resolver and raiser rights',()=>{
 const t={tag:'resolver',raiser:'raiser',owner:'owner',status:'Open'};assert(ticketActionAllowed(t,'retag','raiser'));assert(ticketActionAllowed(t,'retag','owner'));assert(!ticketActionAllowed(t,'retag','resolver'));assert(ticketActionAllowed(t,'resolve','resolver'));assert(!ticketActionAllowed(t,'resolve','raiser'));assert(!ticketActionAllowed(t,'hold','resolver'));assert(ticketActionAllowed(t,'hold','admin',true));assert(!ticketActionAllowed(t,'close','raiser'));assert(ticketActionAllowed({...t,status:'Resolved'},'close','raiser'));assert(!ticketActionAllowed({...t,status:'Closed'},'resolve','resolver'));
});
