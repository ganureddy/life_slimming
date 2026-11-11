import { ccCall } from './cc';
import { session } from '../lib/session';
// Reuse a completed, bounded calendar response within this login only. Appointment
// detail always goes to the server, and refreshKey makes calendar refresh explicit.
const calendarCache = new Map();
export async function requestVisitReport(args, signal, refresh = false) {
  const key=JSON.stringify([session.user,session.roles,args]);
  if(args.view==='calendar'&&!refresh){const item=calendarCache.get(key);if(item&&Date.now()-item.at<60000)return item.data;}
  const data=await ccCall('life_cc_agent_marketing_data',args,signal);
  if(args.view==='calendar'&&!signal?.aborted){calendarCache.set(key,{at:Date.now(),data});if(calendarCache.size>12)calendarCache.delete(calendarCache.keys().next().value);}
  return data;
}
