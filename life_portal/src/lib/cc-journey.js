export const milestoneNames = ['New','Contacted','Interested','Appointment Booked','Appointment Missed','Visited','Visited - Not Booked','Booked - Payment Pending','Joined Client'];
export const journeyFlags = [['','All flags'],...milestoneNames.map(value=>[value,value]),['closed','Closed'],['failed','Last call failed'],['unreachable','Unreachable 3+'],['overdue','Follow-up overdue']];
export function matchesJourney(summary, flag, now = Date.now()) {
  if (!flag) return true;
  if (!summary) return false;
  if (flag === 'closed') return /^(DNC|LOST|INVALID)$/.test(summary.protected || '');
  if (flag === 'failed') return !!summary.last_call_result && summary.last_call_result !== 'Connected';
  if (flag === 'unreachable') return Number(summary.unreachable_streak) >= 3;
  if (flag === 'overdue') return !!summary.next_action_due && new Date(summary.next_action_due.replace(' ', 'T') + '+05:30').getTime() < now;
  return summary.milestone === flag;
}
export function parseLeadCsv(text) {
  const rows = []; let row = [], value = '', quoted = false;
  for (let i=0;i<text.length;i++) {
    const c=text[i];
    if(c==='"') { if(quoted&&text[i+1]==='"'){value+='"';i++;} else quoted=!quoted; }
    else if(c===','&&!quoted){row.push(value.trim());value='';}
    else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(value.trim());if(row.some(Boolean))rows.push(row);row=[];value='';}
    else value+=c;
  }
  if(quoted) throw new Error('CSV contains an unclosed quote.');
  row.push(value.trim());if(row.some(Boolean))rows.push(row);
  const headers=(rows.shift()||[]).map(v=>v.replace(/^\uFEFF/,'').toLowerCase());
  if(!['name','mobile','source','branch'].every(key=>headers.includes(key)))throw new Error('CSV needs name, mobile, source and branch columns.');
  if(rows.length>500)throw new Error('Upload up to 500 leads at a time.');
  return rows.map((values,index)=>({row:index+2,...Object.fromEntries(headers.map((key,i)=>[key,values[i]||'']))}));
}
