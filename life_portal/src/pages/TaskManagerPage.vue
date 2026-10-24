<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { session } from '../lib/session';
import { mountTaskManager } from '../controllers/task-manager';
import { createTaskPageScope } from '../lib/task-page-scope';
import TaskDialogHost from '../components/tasks/TaskDialogHost.vue';
import '../styles/tasks.css';
const root = ref(null), dialogs = ref(null);
const status = reactive({ reads: 0, writes: 0, error: '', notice: '' });
let page, controller;
function refresh() { status.error = ''; controller?.refresh(); }
onMounted(() => {
  page = createTaskPageScope({ root: root.value, session, status, dialogs: dialogs.value });
  controller = mountTaskManager(page);
});
onBeforeRouteLeave(() => !status.writes);
onBeforeUnmount(() => page?.dispose());
</script>
<template>
  <section class="task-manager-page" :aria-busy="status.reads > 0 || status.writes > 0">
    <p v-if="status.error" class="task-page-message task-page-error" role="alert">{{ status.error }} <button type="button" :disabled="status.writes > 0" @click="refresh">Retry</button></p>
    <p v-if="status.notice" class="task-page-message" role="status">{{ status.notice }}</p>
<!-- Task page layout -->
<div id="life-tt-app" ref="root" class="life-tt-app">

  <!-- HEADER -->
<div class="header">

  <div class="life-header-left">

    <a
      href="/app/healthcare"
      class="life-back-btn"
      target="_self"
      title="Go to Healthcare"
    >
      ←
    </a>

    <div>
      <div class="h1">TASK MANAGER &amp; TICKET SYSTEM</div>
      <div class="sub">
        All Branches + Head Office — Internal Workflow &amp; Helpdesk
      </div>
    </div>

  </div>

  <div class="logged-user-box">
    <label>LOGGED IN AS</label>
    <div id="logged-in-user-name">Loading...</div>
    <div id="logged-in-user-role">Please wait...</div>
  </div>

</div>

  <div class="gold-bar"></div>

  <div class="content">

    <!-- TOP MODULE TOGGLE -->
    <div class="type-toggle">
      <div class="type-btn sel" id="toggle-task">
        <div class="tt">
          📋 Task Management
          <span class="cnt" id="task-pending-cnt">0</span>
        </div>
        <div class="ts">Assign, track, and report on internal tasks</div>
      </div>

      <div class="type-btn" id="toggle-ticket">
        <div class="tt">
          🎫 Ticket / Helpdesk
          <span class="cnt" id="ticket-pending-cnt">0</span>
        </div>
        <div class="ts">Raise and resolve issues across all branches</div>
      </div>
    </div>
    
    <div class="life-refresh-row">
      <div class="life-tab-note" id="life-tab-note">
        Select a tab to view its purpose.
      </div>
    
      <div class="life-refresh-actions">
        <span class="life-refresh-note" id="life-refresh-note"></span>
        <button type="button" class="life-refresh-btn" id="life-refresh-btn">
          ↻ Refresh
        </button>
      </div>
    </div>

    <!-- TASK MODULE -->
    <div class="module on" id="module-task">

      <div class="sub-nav">
        <div class="snav on" data-task-sub="0">+ Assign New Task</div>
        <div class="snav" data-task-sub="1">All Tasks Report</div>
        <div class="snav" data-task-sub="2">My Tasks</div>
      </div>

      <!-- ASSIGN NEW TASK -->
      <div class="subpage on" id="task-sub-0">
        <div class="card">
          <div class="card-hdr">Assign New Task</div>

          <div class="card-body">
            <div class="two-col">
              <div class="field-block">
                <label class="lbl">Task Assigned By</label>
                <input type="text" id="task-assignedby" disabled>
              </div>

              <div class="field-block">
                <label class="lbl">Task Assigning To <span class="required-mark">*</span></label>
                <div class="picker-wrap">
                  <input type="text" id="task-assignto-search" placeholder="Type a name to search..." autocomplete="off">
                  <div class="picker-results" id="task-assignto-results"></div>
                </div>
                <div class="selected-chip-row" id="task-assignto-chip"></div>
              </div>
            </div>

            <div class="three-col">
              <div class="field-block">
                <label class="lbl">Task Category <span class="required-mark">*</span></label>
                <select id="task-category">
                  <option value="">Select</option>
                </select>
              </div>

              <div class="field-block">
                <label class="lbl">Task Start Date <span class="required-mark">*</span></label>
                <input type="date" id="task-startdate">
              </div>

              <div class="field-block">
                <label class="lbl">
                  Task Deadline Date & Time <span class="required-mark">*</span>
                  <span id="task-duration-label" class="life-duration-label"></span>
                </label>
                <input type="datetime-local" id="task-deadline">
              </div>
            </div>

            <div class="field-block">
              <label class="lbl">Task Details <span class="required-mark">*</span> max 100 words</label>
              <textarea id="task-details"></textarea>
              <div class="wordcount" id="task-wordcount">0 / 100 words</div>
            </div>

            <div class="field-block">
              <label class="lbl">Task Priority <span class="required-mark">*</span></label>
              <div class="priority-grp" id="task-priority-grp">
                <div class="priority-chip" data-p="High">High</div>
                <div class="priority-chip" data-p="Medium">Medium</div>
                <div class="priority-chip" data-p="Low">Low</div>
              </div>
            </div>

            <div class="field-block">
              <label class="lbl">Once Task Done, Update To</label>
              <div class="picker-wrap">
                <input type="text" id="task-updateto-search" placeholder="Type a name to add another recipient..." autocomplete="off">
                <div class="picker-results" id="task-updateto-results"></div>
              </div>
              <div class="selected-chip-row" id="task-updateto-chip"></div>
            </div>

            <div class="field-block">
              <label class="lbl">Attachments Optional</label>
              <div class="attach-zone" id="task-attach-zone">
                📎 Click to attach files — photos, documents, PDFs
              </div>
              <input type="file" id="task-file-input" multiple style="display:none">
              <div class="attach-list" id="task-attach-list"></div>
            </div>

            <button class="btn btn-n" id="task-submit-btn">✓ Assign Task</button>
          </div>
        </div>
      </div>

      <!-- ALL TASKS REPORT -->
      <div class="subpage" id="task-sub-1">
        <div class="fbar">
          <div>
            <label class="lbl">Category</label>
            <select id="tr-category">
              <option value="">All</option>
            </select>
          </div>

          <div>
            <label class="lbl">Priority</label>
            <select id="tr-priority">
              <option value="">All</option>
              <option>High</option>
              <option>Medium</option>
              <option>Low</option>
            </select>
          </div>

          <div>
            <label class="lbl">Status</label>
            <select id="tr-status">
              <option value="">All</option>
              <option>Open</option>
              <option>Overdue</option>
              <option>Completed</option>
              <option>Cancelled</option>
            </select>
          </div>

          <button class="apbtn" id="task-report-apply">▶ Apply</button>
        </div>

        <div class="tiles" id="task-tiles"></div>

        <div class="card">
          <div class="card-hdr">
            All Tasks
            <span class="badge" id="task-report-count">0</span>
          </div>

          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>Assigned By</th>
                  <th>Assigned To</th>
                  <th>Category</th>
                  <th>Details</th>
                  <th>Priority</th>
                  <th>Update To</th>
                  <th>Attachments</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="task-report-body"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- MY TASKS -->
      <div class="subpage" id="task-sub-2">
        <div class="two-col" style="align-items:start">
          <div class="card">
            <div class="card-hdr">
              Assigned To Me
              <span class="badge" id="mytask-to-count">0</span>
            </div>
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>From</th>
                    <th>Category</th>
                    <th>Deadline</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="mytask-to-body"></tbody>
              </table>
            </div>
          </div>

          <div class="card">
            <div class="card-hdr">
              Assigned By Me
              <span class="badge" id="mytask-by-count">0</span>
            </div>
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>To</th>
                    <th>Category</th>
                    <th>Deadline</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="mytask-by-body"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- TICKET / HELPDESK MODULE -->
    <div class="module" id="module-ticket">

      <div class="sub-nav">
        <div class="snav on" data-ticket-sub="0">+ Raise New Ticket</div>
        <div class="snav" data-ticket-sub="1">All Tickets Report</div>
        <div class="snav" data-ticket-sub="2">My Tickets</div>
      </div>

      <!-- RAISE NEW TICKET -->
      <div class="subpage on" id="ticket-sub-0">
        <div class="card">
          <div class="card-hdr">Raise New Ticket</div>

          <div class="card-body">
            <div class="three-col">
              <div class="field-block">
                <label class="lbl">Raised By</label>
                <input type="text" id="ticket-raisedby" disabled>
              </div>

              <div class="field-block">
                <label class="lbl">Branch</label>
                <select id="ticket-branch"></select>
              </div>

              <div class="field-block">
                <label class="lbl">Priority <span class="required-mark">*</span></label>
                <div class="priority-grp" id="ticket-priority-grp">
                  <div class="priority-chip" data-p="High">High</div>
                  <div class="priority-chip" data-p="Medium">Medium</div>
                  <div class="priority-chip" data-p="Low">Low</div>
                </div>
              </div>
            </div>

            <div class="two-col">
              <div class="field-block">
                <label class="lbl">Issue Category <span class="required-mark">*</span></label>
                <select id="ticket-category">
                  <option value="">Select Category</option>
                </select>
              </div>

              <div class="field-block">
                <label class="lbl">Specific Issue <span class="required-mark">*</span></label>
                <select id="ticket-issue">
                  <option value="">Select Category First</option>
                </select>
              </div>
            </div>

            <div class="field-block" id="ticket-other-block" style="display:none">
              <label class="lbl">Describe the Issue max 100 words</label>
              <textarea id="ticket-other-text"></textarea>
              <div class="wordcount" id="ticket-other-wordcount">0 / 100 words</div>
            </div>

            <div class="field-block" id="ticket-employee-involved-block" style="display:none">
              <label class="lbl">Name of Employee Involved <span class="required-mark">*</span></label>
              <select id="ticket-employee-involved"></select>
            </div>

            <div class="two-col">
              <div class="field-block">
                <label class="lbl">Tag To Resolver <span class="required-mark">*</span></label>
                <div class="picker-wrap">
                  <input type="text" id="ticket-tagto-search" placeholder="Type a name to search..." autocomplete="off">
                  <div class="picker-results" id="ticket-tagto-results"></div>
                </div>
                <div class="selected-chip-row" id="ticket-tagto-chip"></div>
              </div>

              <div class="field-block">
                <label class="lbl">CC To Optional</label>
                <div class="picker-wrap">
                  <input type="text" id="ticket-ccto-search" placeholder="Type a name to add CC..." autocomplete="off">
                  <div class="picker-results" id="ticket-ccto-results"></div>
                </div>
                <div class="selected-chip-row" id="ticket-ccto-chip"></div>
              </div>
            </div>

            <div class="field-block">
              <label class="lbl">Issue Details <span class="required-mark">*</span></label>
              <textarea id="ticket-details" placeholder="Describe what happened..."></textarea>
            </div>

            <div class="field-block">
              <label class="lbl">Attachments Optional</label>
              <div class="attach-zone" id="ticket-attach-zone">
                📎 Click to attach files — photos, screenshots, documents
              </div>
              <input type="file" id="ticket-file-input" multiple style="display:none">
              <div class="attach-list" id="ticket-attach-list"></div>
            </div>

            <button class="btn btn-n" id="ticket-submit-btn">✓ Submit Ticket</button>
          </div>
        </div>
      </div>

      <!-- ALL TICKETS REPORT -->
      <div class="subpage" id="ticket-sub-1">
        <div class="fbar">
          <div>
            <label class="lbl">Category</label>
            <select id="ticr-category">
              <option value="">All</option>
            </select>
          </div>

          <div>
            <label class="lbl">Priority</label>
            <select id="ticr-priority">
              <option value="">All</option>
              <option>High</option>
              <option>Medium</option>
              <option>Low</option>
            </select>
          </div>

          <div>
            <label class="lbl">Status</label>
            <select id="ticr-status">
              <option value="">All</option>
              <option>Open</option>
              <option>Replied</option>
              <option>On Hold</option>
              <option>Resolved</option>
              <option>Closed</option>
            </select>
          </div>

          <button class="apbtn" id="ticket-report-apply">▶ Apply</button>
        </div>

        <div class="tiles" id="ticket-tiles"></div>

        <div class="card">
          <div class="card-hdr">
            All Tickets
            <span class="badge" id="ticket-report-count">0</span>
          </div>

          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>Raised By</th>
                  <th>Branch</th>
                  <th>Category</th>
                  <th>Issue</th>
                  <th>Tag To</th>
                  <th>CC To</th>
                  <th>Priority</th>
                  <th>Attachments</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="ticket-report-body"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- MY TICKETS -->
      <div class="subpage" id="ticket-sub-2">
        <div class="two-col" style="align-items:start">
          <div class="card">
            <div class="card-hdr">
              Tagged To Me / CC'd To Me
              <span class="badge" id="myticket-tome-count">0</span>
            </div>

            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>From</th>
                    <th>Issue</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="myticket-tome-body"></tbody>
              </table>
            </div>
          </div>

          <div class="card">
            <div class="card-hdr">
              Raised By Me
              <span class="badge" id="myticket-byme-count">0</span>
            </div>

            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Issue</th>
                    <th>Tag To</th>
                    <th>Priority</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody id="myticket-byme-body"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- MODAL -->
  <div class="modal-overlay" id="modal">
    <div class="modal-box">
      <div class="mic" id="modal-icon">✅</div>
      <div class="mtt" id="modal-title"></div>
      <div class="mtx" id="modal-text"></div>
      <button class="btn btn-n" id="modal-ok-btn">OK</button>
    </div>
  </div>

</div>
<!-- End task page layout -->
    <TaskDialogHost ref="dialogs" />
  </section>
</template>
<style scoped>
.task-manager-page{min-width:0;width:100%}.task-page-message{margin:0;padding:10px 16px;background:#eff8f0;color:#164b26;font:13px Arial,sans-serif}.task-page-error{background:#fff1ed;color:#97301d}.task-page-message button{margin-left:8px;padding:5px 12px;border:1px solid currentColor;border-radius:6px;background:white;cursor:pointer}
</style>
