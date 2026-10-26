import {request} from '../api/http';
import endpoints from '../api/endpoints.json';
import {session} from './session';
export function createNativeApi(){
 const reads=new Set();let disposed=false;
 async function call(method,args={},write=false,raw=false){if(disposed)throw new DOMException('Page closed','AbortError');const ctrl=new AbortController();if(!write)reads.add(ctrl);try{const body=await request(endpoints[method]||method,{args,csrfToken:session.csrf_token,signal:ctrl.signal});if(disposed)throw new DOMException('Page closed','AbortError');return raw?body:body.message;}finally{reads.delete(ctrl);}}
 async function list(doctype,fields,filters={},order_by='name asc',limit=0){const out=[];for(let start=0;;start+=500){const rows=await call('frappe.client.get_list',{doctype,fields,filters,order_by,limit_start:start,limit_page_length:limit?Math.min(500,limit-out.length):500});if(!Array.isArray(rows))throw Error('Invalid '+doctype+' response.');out.push(...rows);if(rows.length<500||limit&&out.length>=limit)return out;}}
 return {call,list,raw:(method,args)=>call(method,args,false,true),get:(doctype,name)=>call('frappe.client.get',{doctype,name}),insert:doc=>call('frappe.client.insert',{doc},true),save:(doctype,name,fieldname)=>call('frappe.client.set_value',{doctype,name,fieldname},true),
 async upload(doctype,name,file){const formData=new FormData();formData.append('file',file,file.name);formData.append('is_private','1');formData.append('doctype',doctype);formData.append('docname',name);const result=await request('upload_file',{formData,csrfToken:session.csrf_token});if(!result.message?.file_url)throw Error('Upload failed.');return result.message;},
 dispose(){disposed=true;reads.forEach(c=>c.abort());reads.clear();}};
}
export function downloadWorkbook(filename,sheets){
 const escape=value=>String(value??'').replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&apos;'}[c]));
 const xml='<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'+sheets.map(sheet=>'<Worksheet ss:Name="'+escape(sheet.name)+'"><Table>'+[sheet.columns.map(c=>c.l||c.label),...sheet.rows.map(row=>sheet.columns.map(c=>c.v?c.v(row):row[c.k||c.key]))].map((row,i)=>'<Row>'+row.map(value=>'<Cell><Data ss:Type="'+(i&&typeof value==='number'?'Number':'String')+'">'+escape(value)+'</Data></Cell>').join('')+'</Row>').join('')+'</Table></Worksheet>').join('')+'</Workbook>';
 const url=URL.createObjectURL(new Blob([xml],{type:'application/vnd.ms-excel;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=filename+'.xls';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function downloadCsv(filename,rows,columns){const cell=value=>'"'+String(value??'').replace(/"/g,'""')+'"';const csv='\uFEFF'+[columns.map(c=>c.l||c.label),...rows.map(row=>columns.map(c=>c.v?c.v(row):row[c.k||c.key]))].map(row=>row.map(cell).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=filename+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
