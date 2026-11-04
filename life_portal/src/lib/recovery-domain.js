export function recoveryNumber(value) {
  const number = Number(String(value ?? '').replace(/[₹,\s]/g, ''));
  return Number.isFinite(number) ? number : 0;
}
export function maskRecoveryMobile(value) {
  const text = String(value ?? '').trim(), digits = text.replace(/\D/g, '');
  return !text ? '' : digits.length < 4 ? text.replace(/./g, 'X') : `XXXXXX${digits.slice(-4)}`;
}
export function recoveryTotals(rows) {
  const total = { gross:0, collected:0, committed:0, writeoff:0, dispute:0, pending:0, done:0, n:rows.length };
  for (const row of rows) {
    const due=recoveryNumber(row.due), collected=recoveryNumber(row.colAmt), committed=recoveryNumber(row.cmtAmt);
    total.gross+=due;
    if(row.st==='COLLECTED')total.collected+=collected||due;
    else if(row.st==='PARTIAL'){total.collected+=collected;total.committed+=committed;}
    else if(row.st==='COMMITTED')total.committed+=committed;
    else if(row.st==='NOTCOLL')total.writeoff+=due;
    else if(row.st==='DISPUTE')total.dispute+=due;
    else total.pending+=due;
    if(row.st && row.st!=='PENDING')total.done++;
  }
  total.real=total.gross-total.collected-total.writeoff;
  return total;
}
export function recoveryGroups(rows, byEmployee=false) {
  const groups=new Map();
  for(const row of rows){const key=JSON.stringify(byEmployee?[row.emp||'',row.branch||'']:[row.branch||'']);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
  return [...groups].map(([key,items])=>({key,label:byEmployee?items[0].emp||'—':items[0].branch||'—',branch:byEmployee?items[0].branch:'',...recoveryTotals(items)})).sort((a,b)=>b.gross-a.gross);
}
function localDate(value) {
  const text=String(value||'').trim();let match=text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:$|T| )/),year,month,day;
  if(match)[,year,month,day]=match;
  else {match=text.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);if(!match)return null;[,day,month,year]=match;}
  const date=new Date(+year,+month-1,+day);
  return date.getFullYear()===+year&&date.getMonth()===+month-1&&date.getDate()===+day?date:null;
}
export function recoverySchedule(rows, now=new Date()) {
  const today=new Date(now.getFullYear(),now.getMonth(),now.getDate()),tomorrow=new Date(today),end7=new Date(today);
  tomorrow.setDate(today.getDate()+1);end7.setDate(today.getDate()+7);
  const month=today.getMonth()-(today.getDate()<6?1:0);
  const windows=[{name:"Today's Dues",from:today,to:today},{name:"Tomorrow's Dues",from:tomorrow,to:tomorrow},{name:'Next 7 Days',from:tomorrow,to:end7},{name:'This Month',from:new Date(today.getFullYear(),month,6),to:new Date(today.getFullYear(),month+1,5)}];
  return windows.map(window=>{let scheduled=0,invoices=0,confirmed=0,commitments=0;for(const row of rows){const next=localDate(row.nextDue),promise=localDate(row.cmtDate);if(next&&next>=window.from&&next<=window.to){scheduled+=recoveryNumber(row.due);invoices++;}if(['COMMITTED','PARTIAL'].includes(row.st)&&promise&&promise>=window.from&&promise<=window.to){const value=recoveryNumber(row.cmtAmt);confirmed+=value;if(value>0)commitments++;}}return {...window,scheduled,invoices,confirmed,commitments};});
}
export function recoveryCsvCell(value) {
  let text=String(value??'');if(/^[\s]*[=+@-]/.test(text))text="'"+text;
  return /[",\r\n]/.test(text)?`"${text.replace(/"/g,'""')}"`:text;
}
export const recoveryManagerSortKeys=['st','colAmt','colDate','mode','cmtAmt','cmtDate','reasonRemark'];
export function sortRecoveryRows(rows,key,direction='desc') {
  const statusOrder={PENDING:0,COLLECTED:1,COMMITTED:2,PARTIAL:3,NOTCOLL:4,DISPUTE:5};
  const value=row=>key==='st'?(statusOrder[row.st]??99):key==='reasonRemark'?`${row.reason||''} ${row.remark||''}`.trim():['invAmt','paid','due','colAmt','cmtAmt','age'].includes(key)?recoveryNumber(row[key]):['nextDue','colDate','cmtDate'].includes(key)?localDate(row[key])?.getTime()||0:String(row[key]??'').trim();
  const available=row=>key==='st'?!!row.st&&row.st!=='PENDING':['colAmt','cmtAmt'].includes(key)?recoveryNumber(row[key])>0:key==='reasonRemark'?!!`${row.reason||''}${row.remark||''}`.trim():!!String(row[key]??'').trim();
  const compare=(a,b)=>typeof a==='number'&&typeof b==='number'?a-b:String(a).localeCompare(String(b),undefined,{numeric:true,sensitivity:'base'});
  return [...rows].sort((a,b)=>{
    const availability=recoveryManagerSortKeys.includes(key)?Number(available(a))-Number(available(b)):0;
    const result=availability||compare(value(a),value(b))||compare(a.inv||'',b.inv||'');
    return direction==='asc'?result:-result;
  });
}
