const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'..');
const code=fs.readFileSync(path.join(root,'src/lib/appointment-scheduler.js'),'utf8');
const api=vm.runInNewContext(code.replaceAll('export ','')+'\n({appointmentSlots,appointmentTime,appointmentERPTime,appointmentInFuture,appointmentOccupiesSlot,appointmentRoomLabel,appointmentReportArgs,appointmentIndex,appointmentSummary,pendingAppointmentTherapies,rescheduledAppointment})',{Date,Map,Set});
test('appointments retain all 25 half-hour slots and distinguish cancelled/moved history from occupancy',()=>{
 assert.equal(api.appointmentSlots.length,25);assert.equal(api.appointmentSlots[0],'07:00 AM');assert.equal(api.appointmentSlots.at(-1),'07:00 PM');
 assert.equal(api.appointmentTime('13:30:00'),'01:30 PM');assert.equal(api.appointmentERPTime('12:00 PM'),'12:00:00');assert.equal(api.appointmentERPTime('07:30 AM'),'7:30:00');
 const rows=[{name:'A',service_room:'Room',appointment_time:'07:00 AM',call_back_status:'Scheduled'},{name:'B',service_room:'Room',appointment_time:'07:00 AM',call_back_status:'Scheduled'},{name:'C',service_room:'Room',appointment_time:'07:30 AM',call_back_status:'Cancel'},{name:'D',service_room:'Room',appointment_time:'08:00 AM',life_ghost:true}];
 const summary=api.appointmentSummary(rows,['Room']);assert.equal(summary.total,3);assert.equal(summary.cancelled,1);assert.equal(summary.available,24);
 assert.equal(api.appointmentIndex(rows).get('Room||07:00 AM').length,2);
 for(const call_back_status of ['Cancel','Cancelled','Re-Scheduled','Re Scheduled'])assert.equal(api.appointmentOccupiesSlot({call_back_status}),false);
 assert.equal(api.appointmentOccupiesSlot({call_back_status:'Closed'}),true);
});
test('booking checks local future time, literal branch names and valid report order syntax',()=>{
 const now=new Date(2026,9,15,12,30);
 assert.equal(api.appointmentInFuture('2026-10-15','12:30 PM',now),false);assert.equal(api.appointmentInFuture('2026-10-15','01:00 PM',now),true);
 assert.equal(api.appointmentInFuture('2026-10-14','07:00 PM',now),false);assert.equal(api.appointmentInFuture('2026-10-16','07:00 AM',now),true);
 assert.equal(api.appointmentRoomLabel('Room 2 - Clinic (A)','Clinic (A)'),'Room 2');
 const args=api.appointmentReportArgs('Patient Appointment',['name'],[],'appointment_time asc');
 assert.equal(args.order_by,'`tabPatient Appointment`.`appointment_time` asc');
 assert.equal(api.appointmentReportArgs('Branch',['name'],[],'modified desc').order_by,'`tabBranch`.`modified` desc');
});
test('pending concerns preserve plan, service unit, session balances and fallback rules',()=>{
 const plans=api.pendingAppointmentTherapies({service_unit:'Slimming',therapy_plan_details:[{therapy_type:'Cryo',no_of_sessions:5,sessions_completed:2},{therapy_type:'Complete',no_of_sessions:2,sessions_completed:2}]},{name:'PLAN-1',start_date:'2026-10-01'});
 assert.equal(plans.length,1);assert.equal(plans[0].pending,3);assert.equal(plans[0].unit,'Slimming');assert.equal(plans[0].plan,'PLAN-1');
 const fallback=api.pendingAppointmentTherapies({concern:'Skin Treatment',healthcare_service_unit:'Skin'},{name:'PLAN-2'});assert.equal(fallback[0].pending,1);assert.equal(fallback[0].unit,'Skin');
});
test('reschedule preserves existing move history, records the old slot, and saves the new booking as Scheduled',()=>{
 const source={name:'A',appointment_date:'2026-10-15',appointment_time:'7:00:00',service_room:'Room',custom_life_move_history:[{from_date:'2026-10-01'}]};
 const doc=api.rescheduledAppointment(source,'2026-10-16','08:30 AM','agent@example.test');
 assert.equal(doc.call_back_status,'Scheduled');assert.equal(doc.appointment_time,'8:30:00');assert.equal(doc.custom_life_move_history.length,2);assert.equal(source.custom_life_move_history.length,1);
 const history=doc.custom_life_move_history[1];assert.equal(history.from_room,'Room');assert.equal(history.from_time,'7:00:00');assert.equal(history.moved_by,'agent@example.test');
 assert.throws(()=>api.rescheduledAppointment(source,'2026-10-15','07:00 AM','agent'),/different/);
});
test('appointment template, state and rules are owned by Vue without legacy content dependencies',()=>{
 for(const file of ['src/pages/AppointmentSchedulerPage.vue','src/composables/useAppointmentScheduler.js','src/lib/appointment-scheduler.js']){
  const text=fs.readFileSync(path.join(root,file),'utf8');assert(!/portal_pages|PortalSourcePage|<iframe|v-html|innerHTML|\beval\s*\(|new Function\s*\(|window\.frappe/.test(text),file);
 }
 const page=fs.readFileSync(path.join(root,'src/pages/AppointmentSchedulerPage.vue'),'utf8');assert(page.includes('<style scoped src="../styles/appointment-scheduler.css">'));
});
