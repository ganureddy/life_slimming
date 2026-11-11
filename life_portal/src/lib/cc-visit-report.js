import { branchOf, indiaStamp, visitMetrics, visitStatus } from './cc.js';
const iso=d=>d.toISOString().slice(0,10);
export function businessCycle(anchor=indiaStamp().slice(0,10),offset=0){const d=new Date(anchor+'T12:00:00Z');d.setUTCMonth(d.getUTCMonth()-(d.getUTCDate()<6?1:0)+offset,6);const start=iso(d);d.setUTCMonth(d.getUTCMonth()+1,5);return [start,iso(d)];}
export function reportRange(period,today=indiaStamp().slice(0,10)){
 const d=new Date(today+'T12:00:00Z'),shift=n=>iso(new Date(d.getTime()+n*86400000));
 if(period==='week'||period==='lastweek'){const start=-((d.getUTCDay()+6)%7)-(period==='lastweek'?7:0);return [shift(start),shift(start+6)];}
 if(period==='month'||period==='lastmonth'||period==='nextmonth')return businessCycle(today,period==='lastmonth'?-1:period==='nextmonth'?1:0);
 if(period==='tomorrow')return [shift(1),shift(1)];if(period==='yesterday')return [shift(-1),shift(-1)];if(period==='ten')return [today,shift(9)];return [today,today];
}
export function cycleDays(anchor,offset=0){const [from,to]=businessCycle(anchor,offset),days=[];for(let d=new Date(from+'T12:00:00Z');iso(d)<=to;d.setUTCDate(d.getUTCDate()+1))days.push(iso(d));return days;}
export function reportGroups(rows,by='branch',now=indiaStamp()){
 const groups=new Map();for(const row of rows){const key=by==='agent'?(row.lead_owner||'Unassigned'):branchOf(row);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
 return [...groups].map(([key,items])=>{const counts=visitMetrics(items,now);return {key,...counts,notBooked:items.filter(r=>visitStatus(r)==='Visited-Not BKD').length,noShow:items.filter(r=>visitStatus(r)==='Not Visited').length,cancelled:items.filter(r=>/cancel/i.test(visitStatus(r))).length,awaiting:items.filter(r=>visitStatus(r)==='Appt Fixed').length,showup:counts.appointments?Math.round(counts.visits*100/counts.appointments):0,conversion:counts.visits?Math.round(counts.booked*100/counts.visits):0};}).sort((a,b)=>a.key.localeCompare(b.key));
}
export function reportDrilldown(rows,metric,now=indiaStamp()){
 return rows.filter(row=>{const s=visitStatus(row);if(metric==='visits')return s.startsWith('Visited');if(metric==='booked')return s==='Visited-BKD';if(metric==='notBooked')return s==='Visited-Not BKD';if(metric==='noShow')return s==='Not Visited';if(metric==='cancelled')return /cancel/i.test(s);if(metric==='awaiting')return s==='Appt Fixed';if(metric==='pending')return visitMetrics([row],now).pending>0;return true;});
}
export function aggregateMoney(rows,key,nameOf=row=>row[key]||'Unassigned'){
 const groups=new Map();for(const row of rows){const name=nameOf(row);if(!groups.has(name))groups.set(name,{name,count:0,billed:0,paid:0,balance:0});const item=groups.get(name);item.count++;item.billed+=Number(row.with_gst||0);item.paid+=Number(row.paid_with_gst??row.paid??0);item.balance+=Number(row.balance||0);}return [...groups.values()].sort((a,b)=>b.paid-a.paid);
}
