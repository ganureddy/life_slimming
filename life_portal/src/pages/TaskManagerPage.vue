<script setup>
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { session } from '../lib/session';
import { createDomPageRuntime } from '../lib/dom-page-runtime';
import { mountTaskManager } from '../controllers/task-manager';
const root = ref(null), status = reactive({ reads:0, writes:0, error:'', notice:'' });
let runtime;
onMounted(() => { runtime=createDomPageRuntime({root:root.value,session,status}); mountTaskManager(runtime); });
onBeforeRouteLeave(() => !status.writes);
onBeforeUnmount(() => runtime?.dispose());
</script>
<template>
<section class="tasks-page" :aria-busy="status.reads > 0 || status.writes > 0">
<p v-if="status.error" role="alert" class="native-source-error">{{status.error}}</p>
<div ref="root" class="native-page-body"><div v-pre>
<div id="life-tm">
  <div class="hdr">
    <a class="back" href="/app/healthcare" title="Back">←</a>
    <div class="ttl-b"><div class="t" id="h-title">TASK MANAGEMENT PRO</div><div class="s">Branches · Departments · Designations · Employees</div></div>
    <div class="modsw" id="modsw">
      <button class="on" data-mod="task">📋 Tasks <span class="c" id="mc-task">0</span></button>
      <button data-mod="ticket">🎫 Tickets / Helpdesk <span class="c" id="mc-ticket">0</span></button>
    </div>
    <div class="hdr-r">
      <select class="va" id="viewas" style="display:none" title="See the screen exactly as an employee sees it"></select>
      <button class="hbtn" data-act="refresh">↻ Refresh</button>
      <button class="hb" data-help="overview" title="How to use this screen">💡</button>
      <div class="me"><div class="pic" id="me-pic">…</div><div style="min-width:0"><div class="nm" id="me-name">Loading…</div><div class="dg" id="me-role"></div></div></div>
    </div>
  </div>
  <div class="gold"></div>
  <div class="wrap">
    <div id="banners"></div>
    <div class="kpis" id="kpis"></div>
    <div class="tabs" id="tabs"></div>
    <div id="view"><div class="loading"><div class="spin"></div>Loading…</div></div>
  </div>
  <div class="ovl" id="ovl"></div>
  <div class="drawer" id="drawer"></div>
  <div class="ovl" id="ovl2"></div>
  <div class="modal" id="modal"></div>
  <div class="toast" id="toast"></div>
  <input id="fileinp" multiple="" style="display:none" type="file"/>
  <div class="tip" id="tip"></div>
</div>
</div></div></section>
</template>
<style scoped src="../styles/tasks.css"></style>
