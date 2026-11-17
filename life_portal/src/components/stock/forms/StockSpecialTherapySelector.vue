<script setup>
import { computed } from 'vue';
const props = defineProps({
  client: { type: Object, default: null },
  appointments: { type: Array, default: () => [] },
  appointment: { type: String, default: '' },
  appointmentLoading: Boolean,
  therapyLoading: Boolean,
  therapyRows: { type: Array, default: () => [] },
  eligibleRows: { type: Array, default: () => [] },
  selectedTherapies: { type: Array, default: () => [] },
  remainingSessions: { type: Number, default: 0 },
  finance: { type: Object, default: () => ({}) },
  consumableTotal: { type: Number, default: 0 },
  paymentException: Boolean,
  exceptionReason: { type: String, default: '' },
  exceptionOther: { type: String, default: '' }
});
const emit = defineEmits(['update:appointment','update:selectedTherapies','update:paymentException','update:exceptionReason','update:exceptionOther']);
const requiresException = computed(() => props.therapyRows.some(row => props.selectedTherapies.includes(`${row.therapy_plan}::${row.therapy_detail_row}`) && Number(row.stock_eligible_sessions) === 0));
function money(value) { return Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 }); }
function appointmentChanged(event) {
  emit('update:appointment',event.target.value);
  emit('update:selectedTherapies',[]);
  emit('update:paymentException',false);
  emit('update:exceptionReason','');
  emit('update:exceptionOther','');
}
function toggle(key,checked) {
  const selected=new Set(props.selectedTherapies);
  if(checked) selected.add(key); else selected.delete(key);
  emit('update:selectedTherapies',[...selected]);
}
</script>
<template>
  <template v-if="client">
    <label class="stock-form-wide">Future patient appointment
      <select :value="appointment" :disabled="appointmentLoading" @change="appointmentChanged">
        <option value="">{{ appointmentLoading?'Loading appointments…':'Choose appointment' }}</option>
        <option v-for="item in appointments" :key="item.name" :value="item.name">{{ item.name }} · {{ String(item.appointment_date||'').slice(0,10) }} {{ item.appointment_time||'' }} · {{ item.therapy_type1||item.therapy_type||item.concern||'Therapy' }}</option>
      </select>
    </label>
    <div class="stock-form-wide">
      <h3>Remaining therapy services <small v-if="therapyLoading">Loading…</small></h3>
      <p>{{ remainingSessions }} sessions remain across {{ therapyRows.length }} therapy detail row(s). Only choose a service matched to the selected appointment.</p>
      <div class="stock-cards compact"><div><span>Linked invoices paid</span><strong>{{ money(finance.paid) }}</strong></div><div><span>Linked invoices outstanding</span><strong>{{ money(finance.due) }}</strong></div></div>
      <div v-for="row in eligibleRows" :key="`${row.therapy_plan}::${row.therapy_detail_row}`" class="stock-release-form">
        <label><input type="checkbox" :checked="selectedTherapies.includes(`${row.therapy_plan}::${row.therapy_detail_row}`)" @change="toggle(`${row.therapy_plan}::${row.therapy_detail_row}`,$event.target.checked)"> {{ row.therapy_type }} · Plan {{ row.therapy_plan }} · {{ row.remaining_sessions }} remaining ({{ row.completed_sessions }}/{{ row.booked_sessions }} used)<small v-if="Number(row.stock_eligible_sessions)===0">No unused paid sessions verified</small></label>
      </div>
      <p v-if="appointment&&!eligibleRows.length&&!therapyLoading" class="stock-empty">No remaining therapy service matches this appointment.</p>
      <template v-if="selectedTherapies.length">
        <h4>Estimated configured consumables: {{ money(consumableTotal) }}</h4>
        <label v-if="requiresException"><input type="checkbox" :checked="paymentException" @change="emit('update:paymentException',$event.target.checked)"> I confirm an exception request despite no unused paid session</label>
        <label v-if="paymentException">Exception reason<select :value="exceptionReason" @change="emit('update:exceptionReason',$event.target.value)"><option value="">Choose reason</option><option>Stock Issue / System Error</option><option>Approved by Branch Head</option><option>Emergency Treatment</option><option>Other Reason</option></select></label>
        <label v-if="exceptionReason==='Other Reason'">Other exception details<input :value="exceptionOther" @input="emit('update:exceptionOther',$event.target.value)"></label>
      </template>
    </div>
  </template>
</template>