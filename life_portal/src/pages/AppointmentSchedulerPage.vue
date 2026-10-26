<script setup>
import { useAppointmentScheduler } from '../composables/useAppointmentScheduler';
const {root,branch,date,branches,rooms,loading,branchLoading,error,historyError,notice,saving,createOpen,createError,activeSlot,
  patientText,patientInfo,clientDetails,patientSuggestions,clientSearchLoading,patientOpen,categoryText,selectedCategory,categorySuggestions,categorySearchLoading,categoryOpen,
  concernText,selectedConcern,concernOpen,therapyPlans,plansLoading,plansError,detailOpen,detailLoading,detailsError,appointmentDoc,detailName,
  status,rescheduleDate,rescheduleSlot,availableSlots,slotsLoading,summary,cellRows,roomLabel,canAdd,readyToCreate,filteredPlans,slots,statuses,today,timeLabel,statusClass,
  loadBoard,retryBoard,openCreate,closeCreate,queueSearch,selectPatient,loadTherapyPlans,selectCategory,selectConcern,createAppointment,openDetails,closeDetails,
  loadAvailableSlots,saveAppointmentStatus,clickAppointment,closeSuggestions}=useAppointmentScheduler();
</script>

<template>
<div id="client-appointment-page" ref="root">

  <div class="pa-board">

    <div class="pa-header">
      <div>
        <h2>Client Appointment Scheduler</h2>
        <p>View booked and empty room slots branch-wise</p>
      </div>

      <div class="pa-filters">
        <div>
          <label>Branch</label>
          <select class="branch-filter" v-model="branch" :disabled="branchLoading || saving" @change="loadBoard"><option v-if="!branches.length" value="">{{ branchLoading?'Loading...':'No Branches' }}</option><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select>
        </div>

        <div>
          <label>Date</label>
          <input type="date" class="date-filter" v-model="date" :disabled="saving" @change="loadBoard" />
        </div>

        <button type="button" class="refresh-btn" :disabled="loading || branchLoading || saving" @click="retryBoard">{{ loading?'Loading...':'Refresh' }}</button>
      </div>
    </div>

    <p v-if="error" role="alert" class="scheduler-error">{{ error }} <button type="button" @click="retryBoard">Retry</button></p><p v-if="historyError" role="alert" class="scheduler-error">Reschedule history could not load: {{ historyError }} <button type="button" @click="loadBoard">Retry</button></p><p v-if="notice" role="status" class="scheduler-notice">{{ notice }}</p>
    <div class="pa-summary">
      <div class="summary-card">
        <span>Appointments</span>
        <strong class="total-count">{{ summary.total }}</strong>
      </div>

      <div class="summary-card">
        <span>Available Slots</span>
        <strong class="available-count">{{ summary.available }}</strong>
      </div>

      <div class="summary-card">
        <span>Rooms</span>
        <strong class="room-count">{{ rooms.length }}</strong>
      </div>

      <div class="summary-card">
        <span>Cancelled</span>
        <strong class="cancel-count">{{ summary.cancelled }}</strong>
      </div>
    </div>

    <div class="pa-table-wrap" tabindex="0" role="region" aria-label="Daily appointments by service room">
      <table class="pa-table">
        <thead class="pa-table-head"><tr v-if="rooms.length &amp;&amp; !loading"><th>⏱</th><th v-for="room in rooms" :key="room">{{ roomLabel(room) }}</th></tr></thead>
        <tbody class="pa-table-body">
 <tr v-if="loading || branchLoading"><td class="no-data" :colspan="rooms.length+1" role="status">Loading...</td></tr>
 <tr v-else-if="!rooms.length"><td class="no-data">{{ error ? 'Appointments could not load.' : 'No service rooms found for this branch' }}</td></tr>
 <tr v-for="slot in (!loading &amp;&amp; !branchLoading &amp;&amp; rooms.length ? slots : [])" :key="slot"><td class="time-cell">{{ slot }}</td>
  <td v-for="room in rooms" :key="room" :class="{'empty-slot':!cellRows(room,slot).length,'slot-past':!cellRows(room,slot).length &amp;&amp; !canAdd(room,slot)}">
   <div v-if="cellRows(room,slot).length" class="life-slot-pair"><div v-for="(row,rowIndex) in cellRows(room,slot)" :key="row.name+'|'+(row.life_ghost?'history':'real')+'|'+rowIndex" class="appt-cell" :class="row.life_ghost?'life-move-ghost':statusClass(row.call_back_status)" :data-name="row.name" :data-move-date="row.life_ghost?row.life_target_date:undefined" tabindex="0" role="button" @click="clickAppointment(row,$event)" @keydown.enter.prevent="clickAppointment(row,$event)">
    <div class="appt-patient">{{ row.patient }}</div><div class="appt-status">{{ row.life_ghost?'Rescheduled to '+row.life_target_date+' · '+row.life_target_time:row.call_back_status || row.status || 'Scheduled' }}</div><div class="appt-id">{{ row.name.split('-')[1]?.trim() || row.name }}</div>
   </div><button v-if="canAdd(room,slot)" type="button" class="add-appt-btn" :data-room="room" :data-slot="slot" :aria-label="'Add appointment at '+slot+' in '+roomLabel(room)" @click="openCreate(room,slot,$event)">+</button></div>
   <button v-else-if="canAdd(room,slot)" type="button" class="add-appt-btn" :data-room="room" :data-slot="slot" :aria-label="'Add appointment at '+slot+' in '+roomLabel(room)" @click="openCreate(room,slot,$event)">+</button><span v-else>—</span>
  </td>
 </tr>
</tbody>
      </table>
    </div>

    <!-- ADD APPOINTMENT MODAL -->
    <div v-if="createOpen" class="pa-modal" @click.self="closeCreate">
      <div class="pa-modal-box" role="dialog" aria-modal="true" aria-labelledby="scheduler-create-title">

        <div class="modal-head">
          <h3 id="scheduler-create-title">Add Appointment</h3>
          <button type="button" class="modal-close" aria-label="Close" :disabled="saving" @click="closeCreate">×</button>
        </div>

        <div class="modal-body">
 <p v-if="createError" class="scheduler-error" role="alert">{{ createError }}</p>
 <p v-if="plansError" class="scheduler-error" role="alert">{{ plansError }} <button @click="loadTherapyPlans">Retry concerns</button></p>
          <div class="form-grid">

            <div class="form-row client-row">
              <label>Client <span>*</span></label>
              <input
                type="text"
                class="modal-client" v-model="patientText" :disabled="saving" @input="queueSearch('patient',true)" @focus="queueSearch('patient')" @blur="closeSuggestions('patient')"
                placeholder="Search client..."
                autocomplete="off"
              />
              <div v-if="patientOpen" class="client-suggestions"><div v-if="clientSearchLoading" class="client-option" role="status">Searching...</div><template v-else><div v-for="option in patientSuggestions" :key="option.value" class="client-option" @mousedown.prevent="selectPatient(option)"><strong>{{ option.value }}</strong><span>{{ option.description || '' }}</span></div><div v-if="!patientSuggestions.length" class="client-option">No records found</div></template></div>
            </div>

            <div class="form-row">
              <label>Client Details</label>
              <input type="text" class="modal-client-details" :value="clientDetails" readonly />
            </div>

            <div class="form-row">
              <label>Branch <span>*</span></label>
              <select class="modal-branch-select" :value="activeSlot?.branch" disabled><option v-for="name in branches" :key="name" :value="name">{{ name }}</option></select>
            </div>

            <div class="form-row search-row">
              <label>Service Room <span>*</span></label>
              <input
                type="text"
                class="modal-service-room" :value="activeSlot?.room" readonly
                placeholder="Search service room..."
                autocomplete="off"
              />
              <div class="service-room-suggestions hidden"></div>
            </div>

            <div class="form-row search-row">
              <label>Category <span>*</span></label>
              <input
                type="text"
                class="modal-category" v-model="categoryText" :disabled="saving" @input="queueSearch('category',true)" @focus="queueSearch('category')" @blur="closeSuggestions('category')"
                placeholder="Search category..."
                autocomplete="off"
              />
              <div v-if="categoryOpen" class="category-suggestions"><div v-if="categorySearchLoading" class="client-option" role="status">Searching...</div><template v-else><div v-for="option in categorySuggestions" :key="option.value" class="client-option" @mousedown.prevent="selectCategory(option)"><strong>{{ option.value }}</strong><span>{{ option.description || '' }}</span></div><div v-if="!categorySuggestions.length" class="client-option">No records found</div></template></div>
            </div>

            <div class="form-row search-row">
              <label>Concern <span>*</span></label>
              <input
                type="text"
                class="modal-concern" v-model="concernText" :disabled="saving" @input="selectedConcern='';concernOpen=true" @focus="concernOpen=true" @blur="closeSuggestions('concern')"
                placeholder="Search concern..."
                autocomplete="off"
              />
              <div v-if="concernOpen" class="concern-suggestions"><div v-if="plansLoading" class="client-option" role="status">Loading pending concerns...</div><div v-else-if="!patientInfo" class="client-option">Select client first</div><div v-else-if="plansError" class="client-option" role="alert">{{ plansError }} <button @mousedown.prevent="loadTherapyPlans">Retry</button></div><template v-else><div v-for="plan in filteredPlans" :key="plan.plan+'|'+plan.therapy+'|'+plan.unit" class="client-option" @mousedown.prevent="selectConcern(plan)"><strong>{{ plan.therapy }}</strong><span>{{ plan.unit || '-' }} | Pending: {{ plan.pending }} | Done: {{ plan.done }}/{{ plan.total }} | Plan: {{ plan.plan }}<template v-if="plan.start_date"> | Start: {{ plan.start_date }}</template></span></div><div v-if="!filteredPlans.length" class="client-option">No pending concerns found for selected category</div></template></div>
            </div>

            <div class="form-row">
              <label>Date &amp; Time <span>*</span></label>
              <input type="text" class="modal-date-time-label" :value="activeSlot?.date+' | '+activeSlot?.slot" readonly />
            </div>

          </div>

          <div class="slot-preview-box hidden">
            <div class="slot-title">
              <div>
                <b>Schedule:</b>
                <span class="slot-category-label">-</span>
                Time
              </div>
              <div>
                <b>Service Unit:</b>
                <span class="slot-service-label">-</span>
              </div>
            </div>

            <div class="slot-list"></div>
          </div>
        </div>

        <div class="modal-actions">
          <button type="button" class="cancel-btn" :disabled="saving" @click="closeCreate">Cancel</button>
          <button type="button" class="create-btn" :disabled="!readyToCreate" @click="createAppointment">
            {{ saving?'Creating...':readyToCreate?'Create Appointment':'Fill Required Details' }}
          </button>
        </div>

      </div>
    </div>

    <!-- APPOINTMENT DETAILS MODAL -->
    <div v-if="detailOpen" class="appt-detail-modal" @click.self="closeDetails">
      <div class="appt-detail-box" role="dialog" aria-modal="true" aria-labelledby="scheduler-detail-title">

        <div class="modal-head">
          <h3 id="scheduler-detail-title">Appointment Details</h3>
          <button type="button" class="detail-modal-close" aria-label="Close" :disabled="saving" @click="closeDetails">×</button>
        </div>

        <div class="modal-body">
          <div class="appt-detail-content">
            <div v-if="detailLoading" class="detail-loading" role="status">Loading...</div><p v-if="detailsError" class="detail-error" role="alert">{{ detailsError }} <button v-if="!appointmentDoc" @click="openDetails(detailName)">Retry</button></p><div v-if="appointmentDoc" class="detail-grid"><div class="detail-item"><span>Client</span><strong>{{ appointmentDoc.patient_name || appointmentDoc.patient || '-' }}</strong></div><div class="detail-item detail-status-inline"><span>Booking Status</span><select v-model="status" class="detail-status-select" :disabled="saving"><option v-for="option in statuses" :key="option">{{ option }}</option></select></div><div class="detail-item"><span>Mobile</span><strong>{{ appointmentDoc.custom_client_mobile_no || '-' }}</strong></div><div class="detail-item"><span>Gender</span><strong>{{ appointmentDoc.patient_sex || '-' }}</strong></div><div class="detail-item"><span>Branch</span><strong>{{ appointmentDoc.branch || '-' }}</strong></div><div class="detail-item"><span>Service Room</span><strong>{{ roomLabel(appointmentDoc.service_room,appointmentDoc.branch) || '-' }}</strong></div><div class="detail-item"><span>Service Unit</span><strong>{{ appointmentDoc.service_unit || '-' }}</strong></div><div class="detail-item"><span>Concern</span><strong>{{ appointmentDoc.concern || '-' }}</strong></div><div class="detail-item"><span>Date &amp; Time</span><strong>{{ appointmentDoc.appointment_date+' | '+timeLabel(appointmentDoc.appointment_time) || '-' }}</strong></div></div>
          </div>

          <div v-if="appointmentDoc &amp;&amp; status==='Re-Scheduled'" class="reschedule-box">
            <div class="reschedule-grid">

              <div class="form-row">
                <label>New Date</label>
                <input type="date" class="reschedule-date" v-model="rescheduleDate" :min="today()" :disabled="saving" @change="loadAvailableSlots" />
              </div>

              <div class="form-row">
                <label>Available Slots</label>
                <select class="reschedule-slot" v-model="rescheduleSlot" :disabled="saving || slotsLoading"><option value="">{{ slotsLoading?'Loading...':'Select slot' }}</option><option v-for="slot in availableSlots" :key="slot">{{ slot }}</option></select>
              </div>

            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button type="button" class="detail-cancel-btn" :disabled="saving" @click="closeDetails">Close</button>
          <button type="button" class="detail-save-btn" :disabled="saving || detailLoading || !appointmentDoc || slotsLoading" @click="saveAppointmentStatus">{{ saving?'Updating...':'Update Status' }}</button>
        </div>

      </div>
    </div>

  </div>
</div>
</template>

<style scoped src="../styles/appointment-scheduler.css"></style>
