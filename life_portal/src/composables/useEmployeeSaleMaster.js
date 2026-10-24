import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { request } from '../api/http';
import { session } from '../lib/session';
import { normalizeReportRow, buildEmployeeCreditRows, groupEmployeeCredits, groupBranchCredits } from '../lib/employee-sale';

export function useEmployeeSaleMaster() {
  const from=ref(''),to=ref(''),branch=ref(''),booking=ref(''),employee=ref(''),employeeId=ref(''),mode=ref(''),paidFrom=ref(''),paidTo=ref(''),outFrom=ref(''),outTo=ref('');
  const permittedBranches=ref([]),branchRestricted=ref(false),branchReady=ref(false),activeTab=ref(0),quick=ref('month');
  const rawRows=ref([]),invoices=ref([]),credits=ref([]),loading=ref(false),error=ref(''),notice=ref(''),employeeSearch=ref(''),employeeModeSearch=ref('');
  const employees=ref([]),employeeLoading=ref(false),employeeError=ref(''),modes=ref([]),modeError=ref('');
  const generatedAt=ref(''),amountErrors=ref({});
  let controller,branchController,modeController,employeeController,employeeTimer,alive=true;
  const rpc = async (method,args,signal) => {
    const body=await request(method,{args,signal,csrfToken:session.csrf_token});
    if(body.exc)throw new Error('The report request failed. Please try again.');
    return body.message;
  };
  const money=value=>'₹'+Number(value||0).toLocaleString('en-IN',{minimumFractionDigits:0,maximumFractionDigits:2});
  const iso=date=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const dateText=value=>{if(!value)return '';const date=new Date(value);if(Number.isNaN(date.getTime()))return value;return String(date.getDate()).padStart(2,'0')+'-'+['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][date.getMonth()]+'-'+String(date.getFullYear()).slice(-2);};
  const compact=value=>{const n=Number(value||0),a=Math.abs(n),divisor=a>=1e7?1e7:a>=1e5?1e5:a>=1e3?1e3:0;return divisor?`${(n/divisor).toFixed(2).replace(/\.00$/,'').replace(/(\.\d)0$/,'$1')} ${divisor===1e7?'CR':divisor===1e5?'L':'K'}`:'';};
  function cycle(offset=0){const now=new Date(),start=new Date(now.getFullYear(),now.getMonth()+(now.getDate()<6?-1:0)+offset,6);return[iso(start),iso(new Date(start.getFullYear(),start.getMonth()+1,5))];}
  function preset(key){quick.value=key;if(key==='today'||key==='yesterday'){const date=new Date();if(key==='yesterday')date.setDate(date.getDate()-1);from.value=to.value=iso(date);}else if(key==='year'){const now=new Date(),year=now.getMonth()>=3?now.getFullYear():now.getFullYear()-1;from.value=`${year}-04-01`;to.value=`${year+1}-03-31`;}else[from.value,to.value]=cycle(key==='lastmonth'?-1:0);}
  const displayBranch=computed(()=>branch.value||(branchRestricted.value?'All Permitted Branches':'All Branches'));
  const branchOptions=computed(()=>[{value:'',label:branchRestricted.value?'All Permitted Branches':'All Branches'},...permittedBranches.value.map(value=>({value,label:value}))]);
  const bookingOptions=computed(()=>[{value:'',label:'All Booking Types'},...[...new Set(['Call Center','DIRECT WALKIN','Existing Customer','InHouse','Inbound','Reference','Unjoined','Walk In',...rawRows.value.map(row=>row.booking_type).filter(Boolean)])].sort().map(value=>({value,label:value}))]);
  const modeOptions=computed(()=>[{value:'',label:'All Modes of Payment'},...modes.value.map(row=>({value:row.name,label:row.name+(row.type?` [${row.type}]`:'' )}))]);
  async function loadBranches(){branchController?.abort();const current=new AbortController();branchController=current;branchReady.value=false;try{
    const rows=await rpc('frappe.client.get_list',{doctype:'Branch',fields:['name'],limit_page_length:200,order_by:'name asc'},current.signal);
    if(!alive||current.signal.aborted)return;
    const names=[...new Set((rows||[]).map(row=>String(row.name||'').trim()).filter(name=>name&&!['head office','testing branch'].includes(name.toLowerCase())))].sort((a,b)=>a.localeCompare(b));
    permittedBranches.value=names;branchRestricted.value=!(session.user==='Administrator'||session.roles.includes('System Manager'));
    if(branchRestricted.value&&!names.length)throw Error('No permitted Branch was returned for this login.');
    if(branchRestricted.value&&names.length===1)branch.value=names[0];branchReady.value=true;
  }catch(cause){if(alive&&cause.name!=='AbortError')error.value=cause.message;}}
  async function loadModes(){modeController?.abort();const current=new AbortController();modeController=current;modeError.value='';try{const rows=await rpc('frappe.client.get_list',{doctype:'Mode of Payment',fields:['name','type'],limit_page_length:100,order_by:'name asc'},current.signal);if(alive&&!current.signal.aborted)modes.value=rows||[];}catch(cause){if(alive&&cause.name!=='AbortError')modeError.value=cause.message;}}
  function searchEmployees(query=''){clearTimeout(employeeTimer);employeeController?.abort();employeeLoading.value=true;employeeError.value='';employeeTimer=setTimeout(async()=>{
    const current=new AbortController();employeeController=current;try{const args={doctype:'Employee',filters:[['status','=','Active']],fields:['name','employee_name'],limit_page_length:20,order_by:'employee_name asc'};
    if(query)args.or_filters=[['employee_name','like',`%${query}%`],['name','like',`%${query}%`]];
    const rows=await rpc('frappe.client.get_list',args,current.signal);if(alive&&!current.signal.aborted)employees.value=[{label:'All Employees',value:'',displayValue:''},...(rows||[]).map(row=>({label:`${row.employee_name} (${row.name})`,value:row.name,displayValue:row.employee_name}))];
    }catch(cause){if(alive&&cause.name!=='AbortError')employeeError.value=cause.message;}finally{if(alive&&employeeController===current)employeeLoading.value=false;}
  },220);}
  function matchesEmployee(row){const id=employeeId.value.toLowerCase(),text=employee.value.trim().toLowerCase(),ids=[row.referring_employee_id,row.referring_practitioner_id,row.incentive_employee_id].map(value=>String(value||'').toLowerCase());return id?ids.includes(id):!text||[row.referring_employee,row.incentive_employee,...ids].some(value=>String(value||'').toLowerCase().includes(text));}
  function applyLocal(rows){return rows.filter(row=>{
    if(branchRestricted.value&&!permittedBranches.value.includes(row.branch))return false;
    if(branch.value&&row.branch.toLowerCase()!==branch.value.toLowerCase())return false;
    if(booking.value&&row.booking_type.toLowerCase()!==booking.value.toLowerCase())return false;
    if(!matchesEmployee(row))return false;
    if(mode.value&&!row.mode_of_payment.split(',').some(token=>token.trim().toLowerCase().includes(mode.value.trim().toLowerCase())))return false;
    for(const[value,min,max]of[[row.paid_amount_without_gst,paidFrom.value,paidTo.value],[row.outstanding_amount,outFrom.value,outTo.value]])if((min!==''&&value<Number(min))||(max!==''&&value>Number(max)))return false;
    return true;
  });}
  function validateAmounts(){const errors={};for(const[key,min,max]of[['paid',paidFrom.value,paidTo.value],['out',outFrom.value,outTo.value]]){
    if((min!==''&&!/^\d+$/.test(String(min)))||(max!==''&&!/^\d+$/.test(String(max))))errors[key]='Enter whole positive amounts only.';
    else if(min!==''&&max!==''&&Number(min)>Number(max))errors[key]='From amount cannot exceed To amount.';
  }amountErrors.value=errors;return !Object.keys(errors).length;}
  async function reportBranch(target,signal,dates){const result=await rpc('frappe.desk.query_report.run',{report_name:'REFERRAL REPORT – FIXED',filters:JSON.stringify({from_date:dates.from,to_date:dates.to,branch:target||''}),ignore_prepared_report:1,are_default_filters:false},signal);
    const raw=Array.isArray(result?.result)?result.result:[],rows=raw.filter(row=>row&&typeof row==='object'&&!Array.isArray(row)).map(normalizeReportRow).filter(row=>row.invoice);
    if(raw.length&&!rows.length)throw Error('Referral report returned data without Invoice fields; invoice-wise results are required.');
    return target?rows.filter(row=>row.branch===target):rows;
  }
  async function generate(){if(!branchReady.value){await loadBranches();if(!alive||!branchReady.value)return;}
    if(!from.value||!to.value){error.value='Select From and To dates.';return;}if(from.value>to.value){error.value='From Date cannot be after To Date.';return;}if(!validateAmounts()){error.value='Please correct the amount filters.';return;}
    if(branch.value&&!permittedBranches.value.includes(branch.value)){error.value='Select a permitted branch from the list.';return;}
    controller?.abort();const current=new AbortController();controller=current;loading.value=true;error.value='';notice.value='';invoices.value=[];credits.value=[];
    const dates={from:from.value,to:to.value};
    try{const targets=branchRestricted.value&&!branch.value?permittedBranches.value:[branch.value||''];
      // Bound parallel report work for accounts with many permitted branches.
      const groups=[];let next=0;await Promise.all(Array.from({length:Math.min(3,targets.length)},async()=>{while(next<targets.length){const target=targets[next++];groups.push(await reportBranch(target,current.signal,dates));}}));
      if(!alive||current.signal.aborted)return;
      const seen=new Set();rawRows.value=groups.flat().filter(row=>{const key=row.branch+'|'+row.invoice;if(seen.has(key))return false;seen.add(key);return true;});
      invoices.value=applyLocal(rawRows.value);const id=employeeId.value.toLowerCase(),text=employee.value.trim().toLowerCase();
      credits.value=buildEmployeeCreditRows(invoices.value).filter(row=>{const ids=[row.employee_id,row.sales_person_id].map(value=>String(value||'').toLowerCase());return id?ids.includes(id):!text||[row.sales_person_name,...ids].some(value=>String(value||'').toLowerCase().includes(text));});
      employeeSearch.value=employeeModeSearch.value='';generatedAt.value=new Date().toLocaleString('en-IN');
      notice.value=`Loaded ${invoices.value.length.toLocaleString('en-IN')} invoices and ${credits.value.length.toLocaleString('en-IN')} employee credits for ${displayBranch.value}.`;
    }catch(cause){if(alive&&!current.signal.aborted){error.value=cause.message;rawRows.value=[];invoices.value=[];credits.value=[];current.abort();}}
    finally{if(alive&&controller===current)loading.value=false;}
  }
  const allEmployeeRows=computed(()=>groupEmployeeCredits(credits.value));
  const employeeRows=computed(()=>allEmployeeRows.value.filter(row=>(!employeeSearch.value||row.name.toLowerCase().includes(employeeSearch.value.toLowerCase()))&&(!employeeModeSearch.value||row.modes.some(value=>value.toLowerCase().includes(employeeModeSearch.value.toLowerCase())))));
  const branchRows=computed(()=>groupBranchCredits(credits.value));
  const topEmployees=computed(()=>allEmployeeRows.value.slice(0,10));
  const summary=computed(()=>credits.value.reduce((sum,row)=>{sum.paid+=row.paid_amount;sum.tax+=row.tax_amount;sum.ex+=row.paid_amount_without_tax;sum.total+=row.grand_total;sum.out+=row.outstanding_amount;sum.invoices.add(row.invoice);return sum;},{paid:0,tax:0,ex:0,total:0,out:0,invoices:new Set()}));
  const bookings=computed(()=>{const groups=new Map();for(const row of credits.value){const name=row.booking_type||'Unknown',sum=groups.get(name)||{name,invoices:new Set(),ex:0,tax:0,paid:0,out:0};sum.invoices.add(row.invoice);sum.ex+=row.paid_amount_without_tax;sum.tax+=row.tax_amount;sum.paid+=row.paid_amount;sum.out+=row.outstanding_amount;groups.set(name,sum);}return[...groups.values()].sort((a,b)=>b.ex-a.ex);});
  const transactions=computed(()=>[...invoices.value].sort((a,b)=>new Date(b.invoice_date)-new Date(a.invoice_date)));
  const overviewTiles=computed(()=>[['Total Invoices',summary.value.invoices.size||invoices.value.length,'t-pn',false],['Employee Sale (ex-GST)',summary.value.ex,'t-pgr',true],['Allocated GST',summary.value.tax,'t-pg',true],['Employee Sale (w/ GST)',summary.value.paid,'t-pn',true],['Allocated Grand Total',summary.value.total,'t-pg',true],['Allocated Outstanding',summary.value.out,'t-pr',true]]);
  const branchTiles=computed(()=>[['Active Branches',branchRows.value.length,'t-pn',false],['Employee Sale (ex-GST)',summary.value.ex,'t-pgr',true],['Allocated Outstanding',summary.value.out,'t-pr',true],['Total Invoices',summary.value.invoices.size,'t-pg',false]]);
  const topBooking=row=>Object.entries(row.bkCounts).sort((a,b)=>b[1]-a[1])[0]?.[0]||'';
  function reset(){preset('month');branch.value=branchRestricted.value&&permittedBranches.value.length===1?permittedBranches.value[0]:'';booking.value=employee.value=employeeId.value=mode.value=paidFrom.value=paidTo.value=outFrom.value=outTo.value='';amountErrors.value={};employeeSearch.value=employeeModeSearch.value='';generate();}
  const xml=value=>String(value??'').replace(/[<>&'\"]/g,ch=>({'<':'&lt;','>':'&gt;','&':'&amp;',"'":'&apos;','"':'&quot;'}[ch]));
  function download(filename,sheet,headers,rows,numeric){if(!rows.length){error.value='No records match current filters.';return;}
    const body=[headers,...rows].map((row,i)=>'<Row>'+row.map((value,j)=>`<Cell><Data ss:Type="${i&&numeric.includes(j)?'Number':'String'}">${xml(value)}</Data></Cell>`).join('')+'</Row>').join('');
    const blob=new Blob([`<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="${xml(sheet)}"><Table>${body}</Table><WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/><SplitHorizontal>1</SplitHorizontal><TopRowBottomPane>1</TopRowBottomPane></WorksheetOptions></Worksheet></Workbook>`],{type:'application/vnd.ms-excel;charset=utf-8'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;link.click();URL.revokeObjectURL(url);
  }
  const round=value=>Math.round((Number(value||0)+Number.EPSILON)*100)/100;
  function exportAll(){if(!validateAmounts())return;const rows=applyLocal(rawRows.value);download(`Referral_${displayBranch.value}_${from.value}_to_${to.value}.xls`,'Transaction Detail',
    ['Invoice','Invoice Date','Branch','Customer','Client Name','Booking Type','Payment IDs','Payment Dates','Mode of Payment','Sharing Type','Referring Employee','Referring Employee ID','Referring Share ex-GST','Incentive Employee','Incentive Employee ID','Incentive Share ex-GST','Paid ex-GST','GST','Paid w/ GST','Grand Total','Outstanding'],
    rows.map(row=>[row.invoice,dateText(row.invoice_date),row.branch,row.customer,row.client_name,row.booking_type,row.payment_ids,row.payment_dates,row.mode_of_payment,row.sharing_type,row.referring_employee,row.referring_employee_id||row.referring_practitioner_id,round(row.referring_employee_share),row.incentive_employee,row.incentive_employee_id,round(row.incentive_employee_share),round(row.paid_amount_without_gst),round(row.gst_amount),round(row.paid_amount),round(row.grand_total),round(row.outstanding_amount)]),[12,15,16,17,18,19,20]);}
  function exportEmployees(){download(`Referral_EmpWise_${from.value}_to_${to.value}.xls`,'Employee Wise',['Rank','Employee','Branch','Emp ID','Invoices','Paid ex-GST','GST','Paid w/ GST','Grand Total','Outstanding','Top Booking Type','Mode of Payment'],allEmployeeRows.value.map((row,index)=>[index+1,row.name,row.branch,row.empId,row.cnt,round(row.exTax),round(row.tax),round(row.paid),round(row.gt),round(row.out),topBooking(row),row.modes.join('; ')]),[0,4,5,6,7,8,9]);}
  onMounted(()=>{preset('month');loadModes();loadBranches().then(()=>{if(alive&&branchReady.value)generate();});});
  onBeforeUnmount(()=>{alive=false;controller?.abort();branchController?.abort();modeController?.abort();employeeController?.abort();clearTimeout(employeeTimer);});
  return{from,to,branch,booking,employee,employeeId,mode,paidFrom,paidTo,outFrom,outTo,branchRestricted,permittedBranches,branchOptions,bookingOptions,modeOptions,employees,employeeLoading,employeeError,modeError,loadModes,searchEmployees,activeTab,quick,loading,error,notice,generatedAt,amountErrors,validateAmounts,money,compact,dateText,preset,generate,reset,employeeSearch,employeeModeSearch,employeeRows,branchRows,topEmployees,bookings,transactions,overviewTiles,branchTiles,topBooking,exportAll,exportEmployees};
}
