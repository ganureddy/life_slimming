import {marketingReport} from './cc-marketing-report.js';
import {visitStatus} from './cc.js';
export const scorecardMetrics=[['raw','Raw Leads'],['quality','Quality Leads'],['connected','Connected'],['fixed','Appointments Fixed'],['appointments','Appointments Due'],['visits','Walk-ins'],['booked','Booked'],['noShow','Not Visited',false,true],['qualityAppointment','Quality → Appointment %','percent'],['showup','Appointment → Walk-in %','percent'],['conversion','Walk-in → Booked %','percent'],['qualityBooked','Quality → Booked %','percent'],['revenue','Revenue (w/o GST)','money'],['paid','Paid Amount','money'],['balance','Balance','money',true],['average','Avg Ticket','money']];
const percentage=(a,b)=>b?Math.round(a/b*1000)/10:0;
export function agentPeriodMetrics(data,range,owners=null){
 const allow=row=>owners===null||owners.includes(row.lead_owner);
 const rows=(data?.rows||[]).filter(allow),invoices=(data?.cc_invoice_report_summary?.rows||[]).filter(allow);
 const scoped={...data,rows,cc_invoice_report_summary:{...data?.cc_invoice_report_summary,payment_rows:(data?.cc_invoice_report_summary?.payment_rows||[]).filter(allow)}};
 const funnel=marketingReport(scoped,range).totals;
 const appointments=rows.filter(r=>{const day=String(r.custom_appointment_date_and_time||'').slice(0,10);return day>=range.from_date&&day<=range.to_date;});
 const visits=appointments.filter(r=>visitStatus(r).startsWith('Visited')).length,booked=appointments.filter(r=>visitStatus(r)==='Visited-BKD').length;
 const revenue=invoices.reduce((n,r)=>n+Number(r.without_gst||0),0),paid=invoices.reduce((n,r)=>n+Number(r.paid_with_gst??r.paid??0),0),balance=invoices.reduce((n,r)=>n+Number(r.balance||0),0);
 return {raw:funnel.raw,quality:funnel.quality,connected:funnel.connected,fixed:funnel.appointments,appointments:appointments.length,visits,booked,noShow:appointments.filter(r=>visitStatus(r)==='Not Visited').length,qualityAppointment:percentage(funnel.appointments,funnel.quality),showup:percentage(visits,appointments.length),conversion:percentage(booked,visits),qualityBooked:percentage(booked,funnel.quality),revenue,paid,balance,average:booked?Math.round(revenue/booked):0};
}
export function agentBenchmarks(data,range,owner){
 const owners=[...new Set((data?.rows||[]).map(r=>r.lead_owner).filter(Boolean))];
 const all=owners.map(agent=>({agent,...agentPeriodMetrics(data,range,[agent])}));
 const maxRaw=Math.max(1,...all.map(r=>r.raw)),maxAppointments=Math.max(1,...all.map(r=>r.appointments));
 const core=all.filter(r=>r.agent===owner||r.raw>=maxRaw*.1||r.appointments>=maxAppointments*.1);
 const own=core.find(r=>r.agent===owner);if(!own)return {rows:[],core:[],own:null};
 return {own,core,rows:scorecardMetrics.map(([key,label,type,inverse])=>{const average=core.reduce((n,r)=>n+r[key],0)/(core.length||1),best=Math.max(0,...core.map(r=>r[key])),rank=[...core].sort((a,b)=>inverse?a[key]-b[key]:b[key]-a[key]).findIndex(r=>r.agent===owner)+1;return {key,label,type,inverse,value:own[key],average,best,difference:average?(own[key]-average)/average*100:null,rank};})};
}
