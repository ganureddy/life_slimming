import { test } from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { FORM_DOCTYPE, sectionFilters, sectionSearch, maskPhone, maskText, displayValue, sameOriginFile, indiaDate, followDocument, visibleFields, childColumns } from '../src/lib/unjoined.js';
import { workbook } from '../src/lib/xlsx.js';
const section = { key: 'clients', dt: 'Patient', branch: 'custom_branch', date: 'custom_joining_date', name: 'patient_name', mobile: 'mobile', base: [['custom_final_decision', '=', 'Not-Booked']] };
const filters = { from: '2026-10-01', to: '2026-10-13', basis: 'business', branch: '', followStatus: '', search: 'Ravi' };
globalThis.crypto ??= webcrypto;
test('business and creation filters include the whole last day and exclude Testing Branch', () => {
 assert.deepEqual(sectionFilters(section, filters), [['custom_final_decision', '=', 'Not-Booked'], ['custom_branch', '!=', 'Testing Branch'], ['custom_joining_date', '>=', '2026-10-01'], ['custom_joining_date', '<', '2026-10-14']]);
 assert.deepEqual(sectionFilters(section, {...filters, branch:'Branch A', basis:'created'}).slice(1), [['custom_branch','=','Branch A'], ['creation','>=','2026-10-01'], ['creation','<','2026-10-14']]);
 assert.deepEqual(sectionSearch(section, filters), [['name','like','%Ravi%'],['patient_name','like','%Ravi%'],['mobile','like','%Ravi%']]);
});
test('masking covers notes, phone fields and nested children while preserving dates', () => {
 assert.equal(maskPhone('9876543210'), '987****210');
 assert.equal(maskText('Call 9876543210 on 2026-10-13'), 'Call 987****210 on 2026-10-13');
 assert.equal(maskText('9876543210',true), '9876543210');
 assert.equal(displayValue('children',[{phone:'9876543210',note:'Call 9123456789'}]), '[{"phone":"987****210","note":"Call 912****789"}]');
});
test('attachments reject external and executable URLs', () => {
 assert.equal(sameOriginFile('/private/files/photo.png','https://local.test'), 'https://local.test/private/files/photo.png');
 for(const value of ['', 'javascript:alert(1)', 'https://outside.test/photo.png'])assert.equal(sameOriginFile(value,'https://local.test'),'');
});
test('source linking uses stable unique keys and rejects a conflicting existing form', async () => {
 const context={section,source:{name:'PAT-1'},form:null};
 const first=await followDocument(context,{client_name:'Ravi',contact_number:'9876543210'});
 const second=await followDocument(context,{client_name:'Ravi'});
 assert.equal(first.doctype,FORM_DOCTYPE);assert.equal(first.custom_source_key,second.custom_source_key);assert.equal(first.custom_source_key.length,64);assert.equal(first.custom_linked_client,'PAT-1');assert.equal(first.custom_source_doctype,'Patient');assert.equal(first.custom_source_document,'PAT-1');
 assert.match(first.client_full_name,/Ravi · UJ-[a-f0-9]{16}/);
 await assert.rejects(followDocument({...context,form:{custom_source_doctype:'Lead',custom_source_document:'LEAD-2'}},{client_name:'Ravi'}),/different source/);
});
test('details omit password, privileged and layout fields; child rows omit ERP bookkeeping', () => {
 assert.deepEqual(visibleFields([{fieldname:'phone',fieldtype:'Data'},{fieldname:'secret',fieldtype:'Password'},{fieldname:'private',fieldtype:'Data',permlevel:1},{fieldname:'blank',fieldtype:'Data'}],{phone:'9876543210',secret:'hidden',private:'hidden',blank:''}).map(f=>f.fieldname),['phone']);
 assert.deepEqual(childColumns([{name:'ROW',parent:'PAT-1',idx:1,therapy:'Slimming',mobile:'9876543210'}]),['therapy','mobile']);
});
test('dates use India midnight and XLSX cells remain text instead of formulas',async()=>{
 assert.equal(indiaDate(new Date('2026-10-12T20:00:00Z')),'2026-10-13');
 const bytes=new Uint8Array(await workbook([{name:'Clients',rows:[['Name'],['=HYPERLINK("bad")']]}]).arrayBuffer());
 assert.deepEqual(Array.from(bytes.slice(0,4)),[80,75,3,4]);
 const text=new TextDecoder().decode(bytes);assert(text.includes('t="inlineStr"'));assert(text.includes('=HYPERLINK(&quot;bad&quot;)'));assert(!text.includes('<f>'));
});
