// Classification copied from the live Branch Visit Report (11 November 2026).
import {branchOf} from './cc.js';
const norm=v=>String(v||'').trim().toLowerCase();
  const JUNK_LEAD_STATUSES = new Set([
    "do not contact","not enquired","nid","wrong number","job enquiry","other clinic","existing client"
  ]);
  const JUNK_CC_SUB_STATUSES = new Set([
    "invalid number","junk/wrong call","existing client","wrong number","job enquiry","other clinic",
    "not enquired","do not contact","nid"
  ]);
  const CONNECTED_LEAD_STATUSES = new Set([
    "replied","opportunity","quotation","lost quotation","interested","converted","call back","get back",
    "consultation done","appointment booked","joined","not interested","existing client","followup","do not contact"
  ]);
  const CONNECTED_CC_SUB_STATUSES = new Set([
    "appointment booked","walked in & booked","very positive","existing client","call & confirm",
    "callback: scheduled","price negotiation","out station","walked in: not booked","joined competition",
    "not interested","distance","do not contact"
  ]);
  const APPOINTMENT_OUTCOMES = new Set([
    "booked","cancelled","not visited","visited","visited not booked","visited booked"
  ]);
  const VISITED_BOOKED_OUTCOMES = new Set(["visited booked"]);
  const VISITED_UNBOOKED_OUTCOMES = new Set(["visited not booked"]);
  const VISITED_PENDING_OUTCOMES = new Set(["visited"]);

  function isJunk(lead){
    const stage=norm(lead.custom_cc_stage);
    const status=norm(lead.status);
    const sub=norm(lead.custom_cc_sub_status);
    return stage==="invalid" || JUNK_LEAD_STATUSES.has(status) || JUNK_CC_SUB_STATUSES.has(sub);
  }
  function isConnected(lead){
    const stage=norm(lead.custom_cc_stage);
    const status=norm(lead.status);
    const sub=norm(lead.custom_cc_sub_status);
    if(CONNECTED_LEAD_STATUSES.has(status) || CONNECTED_CC_SUB_STATUSES.has(sub)) return true;
    return stage==="follow-up" || stage==="success";
  }
  function hasAppointment(lead){
    const ap=norm(lead.custom_appointment_status);
    const status=norm(lead.status);
    const sub=norm(lead.custom_cc_sub_status);
    if(status==="appointment booked" || sub==="appointment booked" || sub==="call & confirm") return true;
    return !!lead.custom_appointment_date_and_time && APPOINTMENT_OUTCOMES.has(ap);
  }
  function visitOutcome(lead){
    const ap=norm(lead.custom_appointment_status);
    const sub=norm(lead.custom_cc_sub_status);

    /* Appointment Status is authoritative. CC Sub Status is fallback only.
       This prevents one Lead from being counted in both Booked and Unbooked. */
    if(VISITED_BOOKED_OUTCOMES.has(ap)) return "booked";
    if(VISITED_UNBOOKED_OUTCOMES.has(ap)) return "unbooked";
    if(VISITED_PENDING_OUTCOMES.has(ap)) return "visited";
    if(sub==="walked in & booked") return "booked";
    if(sub==="walked in: not booked") return "unbooked";
    return "";
  }
  function isVisitedBooked(lead){ return visitOutcome(lead)==="booked"; }
  function isVisitedUnbooked(lead){ return visitOutcome(lead)==="unbooked"; }
  function isVisited(lead){ return !!visitOutcome(lead); }
  function isBooked(lead){ return isVisitedBooked(lead); }
  function isQuality(lead){
    /* In this report Quality and Junk are an exact partition of Raw Leads. */
    return !isJunk(lead);
  }


export function marketingReport(data,range,filters={}) {
 const unique=[...new Map((data?.rows||[]).filter(r=>r.name).map(r=>[r.name,r])).values()];
 const match=r=>(!filters.agencies?.length||filters.agencies.includes(r.source||'Unspecified'))&&(!filters.category||(r.enquired_for||'Unspecified')===filters.category)&&(!filters.branch||branchOf(r)===filters.branch)&&(!filters.query||[r.name,r.lead_name,r.source,r.ad_set,r.campaign_name].some(v=>String(v||'').toLowerCase().includes(filters.query.toLowerCase())));
 const inside=value=>{const d=String(value||'').slice(0,10);return d>=range.from_date&&d<=range.to_date;};
 const received=unique.filter(r=>inside(r.custom_posting_date||r.creation)&&match(r));
 const visits=unique.filter(r=>inside(r.custom_appointment_date_and_time)&&isVisited(r)&&match(r));
 const payments=(data?.cc_invoice_report_summary?.payment_rows||[]).filter(r=>r.therapy_plan&&norm(r.therapy_plan_media)==='call center'&&Number(r.therapy_plan_already_taken)!==1&&Number(r.paid)>0&&inside(r.payment_date)&&match({...r,branch:r.lead_branch||r.branch}));
 function aggregate(r,v,f){const booked=v.filter(isBooked).length,paid=f.reduce((n,x)=>n+Number(x.paid||0),0),quality=r.filter(isQuality).length,appointments=r.filter(hasAppointment).length;return {raw:r.length,quality,junk:r.filter(isJunk).length,connected:r.filter(isConnected).length,appointments,pending:Math.max(0,quality-appointments),visits:v.length,booked,unbooked:v.filter(isVisitedUnbooked).length,paid,outstanding:f.filter(x=>x.is_later_collection).reduce((n,x)=>n+Number(x.paid||0),0),leadVisit:r.length?Math.round(v.length/r.length*100):0,conversion:v.length?Math.round(booked/v.length*100):0,average:booked?Math.round(paid/booked):0,adSets:new Set(r.concat(v,f).map(x=>x.ad_set).filter(Boolean)).size};}
 function groups(field){const value=r=>String(field==='branch'?branchOf(r):(r[field]||'Unspecified'));return [...new Set(received.concat(visits,payments).map(value))].sort().map(name=>{const groupReceived=received.filter(r=>value(r)===name),groupVisits=visits.filter(r=>value(r)===name),groupPayments=payments.filter(r=>value(r)===name),members=groupReceived.concat(groupVisits,groupPayments),campaigns=[...new Set(members.map(r=>r.campaign_name).filter(Boolean))].map(name=>data?.campaign_details?.[name]).filter(Boolean);
 return {name,...aggregate(groupReceived,groupVisits,groupPayments),branchRatios:[...new Set(members.map(branchOf))].sort().map(branch=>{const a=aggregate(groupReceived.filter(r=>branchOf(r)===branch),groupVisits.filter(r=>branchOf(r)===branch),groupPayments.filter(r=>branchOf(r)===branch));return branch+': '+a.conversion+'% ('+a.booked+'/'+a.visits+')';}).join(' · '),spend:null,enquiredFor:[...new Set(members.map(r=>r.enquired_for).filter(Boolean))].join(' · '),start:campaigns.map(r=>r.from_date).filter(Boolean).sort()[0]||'',end:campaigns.map(r=>r.to_date).filter(Boolean).sort().at(-1)||'',status:[...new Set(campaigns.map(r=>r.status).filter(Boolean))].join(' · ')};});}

 return {totals:aggregate(received,visits,payments),received,appointments:received.filter(hasAppointment),quality:received.filter(isQuality),pending:received.filter(r=>isQuality(r)&&!hasAppointment(r)),junk:received.filter(isJunk),connected:received.filter(isConnected),booked:visits.filter(isBooked),unbooked:visits.filter(isVisitedUnbooked),visits,payments,agency:groups('source'),campaign:groups('ad_set'),category:groups('enquired_for'),branches:groups('branch')};
}
