const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Print all loaded records, rather than only the current table's 40-row page.
export function printReportTable(title,columns,rows) {
 const popup=window.open('','_blank','width=1200,height=850');
 if(!popup)return false;
 const html='<!doctype html><html><head><meta charset="utf-8"><title>'+escape(title)+'</title><style>body{font:12px Poppins,Arial,sans-serif;color:#16402d;padding:20px}h1{font-size:20px}table{width:100%;border-collapse:collapse}th,td{padding:7px;border:1px solid #d4e6d9;text-align:left;white-space:pre-line}th{background:#e6f5ea}thead{display:table-header-group}tr{break-inside:avoid}@page{size:landscape;margin:12mm}</style></head><body><h1>'+escape(title)+'</h1><p>'+rows.length+' records</p><table><thead><tr>'+columns.map(c=>'<th>'+escape(c.label)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+columns.map(c=>'<td>'+escape(c.value?c.value(row):row[c.key])+'</td>').join('')+'</tr>').join('')+'</tbody></table></body></html>';
 popup.document.open();popup.document.write(html);popup.document.close();popup.addEventListener('load',()=>{popup.focus();popup.print();},{once:true});
 return true;
}
