import { visitStatus } from './cc.js';
// Weights and low-volume conversion rules from lifePremiumRanking in the reference.
export function rankReportAgents(appointments, received, inputs={}, restrictedOwner='') {
 const owners=[...new Set([...appointments,...received].map(r=>r.lead_owner).filter(Boolean))];
 const result=owners.map(agent=>{
  const rows=appointments.filter(r=>r.lead_owner===agent),visits=rows.filter(r=>visitStatus(r).startsWith('Visited')).length,booked=rows.filter(r=>visitStatus(r)==='Visited-BKD').length;
  const input=inputs[agent]||{},valid=Number(input.bookingTarget)>0&&Number(input.visitTarget)>0&&['handling','followup'].every(k=>input[k]!==''&&input[k]!==undefined&&Number.isFinite(Number(input[k]))&&Number(input[k])>=0&&Number(input[k])<=100);
  const bookingAchievement=valid?Math.min(100,booked/Number(input.bookingTarget)*100):null,visitAchievement=valid?Math.min(100,visits/Number(input.visitTarget)*100):null,pct=visits?booked/visits*100:null,conversionWeight=visits<5?0:visits<10?.5:1;
  const score=valid?bookingAchievement*.35+visitAchievement*.25+(pct||0)*.2*conversionWeight+Number(input.handling)*.1+Number(input.followup)*.1:null;
  return {agent,booked,visits,total:rows.length,leads:restrictedOwner&&agent!==restrictedOwner?null:received.filter(r=>r.lead_owner===agent).length,input,pct,score,bookingAchievement,visitAchievement,conversionWeight};
 });
 result.sort((a,b)=>(b.score??-1)-(a.score??-1)||b.booked-a.booked||b.visits-a.visits||a.agent.localeCompare(b.agent));
 let rank=0;return result.map(row=>({...row,rank:row.score===null?null:++rank}));
}
