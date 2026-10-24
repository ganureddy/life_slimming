const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'..');
const source=fs.readFileSync(path.join(root,'src/lib/employee-sale.js'),'utf8');
const api=vm.runInNewContext(source.replaceAll('export ','')+'\n({normalizeReportRow,buildEmployeeCreditRows,groupEmployeeCredits,groupBranchCredits})');
const invoice=extra=>api.normalizeReportRow({invoice:'INV-1',invoice_date:'2026-10-15',branch:'Clinic A',paid_amount:1050,paid_amount_without_gst:1000,gst_amount:50,grand_total:2100,outstanding_amount:1050,referring_employee:'Priya',referring_employee_id:'EMP-1',incentive_employee:'Arun',incentive_employee_id:'EMP-2',referring_employee_share:600,incentive_employee_share:400,...extra});
test('employee allocation conserves invoice totals and combines the same employee in both roles',()=>{
 const credits=api.buildEmployeeCreditRows([invoice()]);
 for(const key of ['paid_amount','gst_amount','grand_total','outstanding_amount'])assert.equal(credits.reduce((n,r)=>n+r[key],0),invoice()[key]);
 assert.equal(credits[0].paid_amount_without_gst,600);assert.equal(credits[1].paid_amount_without_gst,400);
 const combined=api.buildEmployeeCreditRows([invoice({incentive_employee_id:' emp-1 ',incentive_employee:'Priya'})]);
 assert.equal(combined.length,1);assert.equal(combined[0].paid_amount_without_gst,1000);assert.equal(combined[0].paid_amount,1050);
});
test('employee identity learns only unambiguous name aliases and keeps practitioner identities distinct',()=>{
 const credits=api.buildEmployeeCreditRows([invoice(),invoice({invoice:'INV-2',referring_employee_id:'',referring_employee:' Priya\u00a0',incentive_employee:'',incentive_employee_share:0,referring_employee_share:1000})]);
 const groups=api.groupEmployeeCredits(credits);
 assert.equal(groups.length,2);const priya=groups.find(r=>r.name==='Priya');assert.equal(priya.cnt,2);assert.equal(priya.exTax,1600);assert.equal(priya.empId,'EMP-1');
 const ambiguous=api.groupEmployeeCredits([{...credits[0],employee_id:'EMP-1'},{...credits[0],employee_id:'EMP-3'},{...credits[0],employee_id:'',sales_person_id:'PRAC-9'}]);
 assert.equal(ambiguous.length,3);
 const branches=api.groupBranchCredits(credits);assert.equal(branches[0].cnt,2);assert.equal(branches[0].emps.length,3);
});
test('employee normalization supports old report aliases and legacy exports retain all transaction fields',()=>{
 const row=api.normalizeReportRow({invoice:'OLD',credit_type:'incentive',sales_person_name:'Arun',employee_id:'EMP-2',paid_amount:1050,paid_amount_without_tax:1000,tax_amount:50,client_name:'Client',sharing_type:'Single'});
 assert.equal(row.incentive_employee,'Arun');assert.equal(row.incentive_employee_share,1000);assert.equal(row.gst_amount,50);assert.equal(row.client_name,'Client');assert.equal(row.sharing_type,'Single');
 for(const file of ['src/pages/EmployeeSaleMasterPage.vue','src/composables/useEmployeeSaleMaster.js','src/lib/employee-sale.js','src/components/employee-sale/ReportSearchSelect.vue']){
 const text=fs.readFileSync(path.join(root,file),'utf8');assert(!/portal_pages|PortalSourcePage|<iframe|v-html|innerHTML|\beval\s*\(|new Function\s*\(|window\.frappe/.test(text),file);
 }
});
