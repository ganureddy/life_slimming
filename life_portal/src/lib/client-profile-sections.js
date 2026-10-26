import {CFG} from './client-info.js';

export function safeFileUrl(raw){
 if(typeof raw!=='string'||!raw.trim()||/^[\s\\]/.test(raw))return '';
 if(/^\/(?:private\/)?files\/[^\s]/.test(raw))return raw;
 try{const u=new URL(raw);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password?u.href:'';}catch{return '';}
}
export const plainText=value=>String(value??'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
export const fileType=url=>/\.(jpe?g|png|gif|webp|bmp|heic|heif)(?:\?|$)/i.test(url)?'image':/\.pdf(?:\?|$)/i.test(url)?'pdf':/\.(mp4|mov|m4v|webm|avi|3gp)(?:\?|$)/i.test(url)?'video':'doc';
export function documentCategory(f){const t=[f.name,f.field,f.doctype].join(' ').replace(/[_-]/g,' ');return /aadh?aa?r/i.test(t)?'🪪 Aadhaar':/pan ?card/i.test(t)?'💳 PAN':/before|pre treatment/i.test(t)&&f.type==='image'?'📷 Before':/after|post treatment/i.test(t)&&f.type==='image'?'📸 After':/pd ?form|pd image|pd document/i.test(t)?'📝 PD form':/consent/i.test(t)?'✍️ Consent':/loan|declaration/i.test(t)?'🎥 Loan':/screenshot|receipt|proof/i.test(t)?'🧾 Payment proof':f.type==='image'?'🖼️ Image':f.type==='video'?'🎬 Video':f.type==='doc'||f.type==='pdf'?'📄 Document':'📎 Other';}

export async function linkedClientRecords(reader,doctypes,bundle){
 const records=[],warnings=[];
 for(const doctype of doctypes){
  try{const fields=await reader.meta(doctype);const patient=fields.find(f=>f.fieldtype==='Link'&&f.options==='Patient')||fields.find(f=>['client','patient','custom_client','custom_patient'].includes(f.fieldname));const customer=!patient&&bundle.patient.customer&&fields.find(f=>f.fieldtype==='Link'&&f.options==='Customer');const link=patient||customer;if(!link)continue;
   const rows=await reader.list(doctype,[[link.fieldname,'=',patient?bundle.pid:bundle.patient.customer]],['*'],300);records.push(...rows.map(row=>({doctype,fields,row})));
  }catch(e){if(e.name==='AbortError')throw e;if(!['DoesNotExistError','NotFoundError'].includes(e.code))warnings.push(doctype+': '+e.message);}
 }
 return {records,warnings};
}

export async function loadClientDocuments(reader,bundle){
 const files=[],seen=new Set();
 function push(raw,name,doctype,docname,field,modified){const url=safeFileUrl(raw);if(!url||doctype==='Sales Invoice')return;const key=url.split('?')[0];if(seen.has(key))return;seen.add(key);let fallback=key.split('/').pop();try{fallback=decodeURIComponent(fallback);}catch{}const f={url,name:name||fallback,doctype,docname,field,modified,type:fileType(url)};f.catLabel=documentCategory(f);files.push(f);}
 function scan(doctype,doc,depth=0,path=''){if(!doc||depth>2)return;for(const [k,v] of Object.entries(doc)){if(Array.isArray(v))v.forEach(row=>scan(doctype,{name:doc.name,modified:doc.modified,...row},depth+1,k));else if(/image|photo|attach|file|document|before|after|consent|pd|video|loan|aadh|pan|screenshot|receipt|proof/i.test(k))push(v,null,doctype,doc.name,path?path+'.'+k:k,doc.modified);}}
 scan('Patient',bundle.patient);
 const paymentFilters=[['docstatus','=',1],['payment_type','=','Receive']];let pays=bundle.patient.customer?await reader.list('Payment Entry',[...paymentFilters,['party','=',bundle.patient.customer]],['name'],2000):[];
 if(!pays.length&&bundle.patient.patient_name)pays=await reader.list('Payment Entry',[...paymentFilters,['party_name','=',bundle.patient.patient_name]],['name'],2000);
 const groups=[['Patient',[bundle.pid]],['Therapy Plan',bundle.plans.map(r=>r.name)],['Therapy Session',bundle.sessions.map(r=>r.name)],['Patient Appointment',bundle.appts.map(r=>r.name)],['Payment Entry',pays.map(r=>r.name)],['Client Followup',bundle.followups.map(r=>r.name)]];
 for(const [dt,names] of groups)if(names.length){const rows=await reader.chunks(names,chunk=>reader.list('File',[['attached_to_doctype','=',dt],['attached_to_name','in',chunk]],['name','file_name','file_url','attached_to_name','attached_to_field','modified'],5000));for(const r of rows)push(r.file_url,r.file_name,dt,r.attached_to_name,r.attached_to_field,r.modified);}
 const paymentDocs=await reader.pool(pays.slice(0,40),p=>reader.doc('Payment Entry',p.name));paymentDocs.forEach(d=>scan('Payment Entry',d));
 return files.sort((a,b)=>String(b.modified).localeCompare(String(a.modified)));
}

export async function loadClientStock(reader,bundle){
 const fields=['name','transaction_date','creation','owner','docstatus','material_request_type','custom_stock_request_type','custom_stock_request_status','custom_client_name','set_warehouse'];
 const [byId,byName,entries]=await Promise.all([reader.list('Material Request',[['custom_client','=',bundle.pid]],fields,300),reader.list('Material Request',[['custom_client_name','=',bundle.patient.patient_name||'~']],fields,300),reader.call(CFG.STOCK_API,{patient:bundle.pid})]);
 if(!Array.isArray(entries))throw Error('Stock entries returned an invalid response.');
 const names=[...new Set([...byId,...byName].map(r=>r.name))],mr=await reader.pool(names,name=>reader.doc('Material Request',name));const map=new Map();for(const row of entries){if(!row.stock_entry)continue;const group=map.get(row.stock_entry)||{h:row,items:[]};group.items.push(row);map.set(row.stock_entry,group);}
 return {mr:mr.sort((a,b)=>String(b.transaction_date||b.creation).localeCompare(String(a.transaction_date||a.creation))),se:[...map.values()]};
}

export async function loadClientConversions(reader,bundle){
 const defs=[{kind:'P2P',doctype:CFG.CONVERSION_DOCTYPE,fields:['client_name']},{kind:'C2C',doctype:'Client Package Conversion Client To Client',fields:['transferor_full_name','client_full_name','client_name']},{kind:'B2B',doctype:'Client Transfer Request Form',fields:['client_full_name','client_name']}],records=[],warnings=[];
 for(const def of defs){const names=new Set();for(const field of def.fields){try{const rows=await reader.list(def.doctype,[[field,'=',bundle.pid]],['name'],1000);rows.forEach(r=>names.add(r.name));}catch(e){if(e.name==='AbortError')throw e;warnings.push(def.kind+' '+field+': '+e.message);}}
  await reader.pool([...names],async name=>{try{records.push({...def,doc:await reader.doc(def.doctype,name)});}catch(e){if(e.name==='AbortError')throw e;warnings.push(def.kind+' '+name+': '+e.message);}});
 }
 return {records:records.sort((a,b)=>String(b.doc.creation||'').localeCompare(String(a.doc.creation||''))),warnings};
}

export async function saveClientRemark(reader,bundle,text){
 const patient=await reader.doc('Patient',bundle.pid),old=String(patient.custom_remarks||'').trim(),entry=new Date().toLocaleString('en-IN',{hour12:true})+' | '+text,combined=old?old+'\n'+entry:entry;
 await reader.call('frappe.client.set_value',{doctype:'Patient',name:bundle.pid,fieldname:'custom_remarks',value:combined});
 const verified=await reader.doc('Patient',bundle.pid);if(String(verified.custom_remarks||'')!==combined)throw Error('Patient Remarks field did not confirm the update. Check Patient write permission.');
 let warning='';try{await reader.call('frappe.client.insert',{doc:{doctype:'Comment',comment_type:'Comment',reference_doctype:'Patient',reference_name:bundle.pid,content:text.replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]))}});}catch(e){warning=e.message;}
 return {patient:verified,warning};
}
