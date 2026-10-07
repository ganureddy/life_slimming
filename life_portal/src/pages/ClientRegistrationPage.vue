<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { billingCall } from '../api/billing';
import { billingBranches } from '../lib/billing';
import BillingRegistration from '../components/billing/BillingRegistration.vue';
import '../styles/billing-native.css';

const router = useRouter();
const bootstrap = ref(null), branches = ref([]), branch = ref('');
const busy = ref(false), error = ref(''), registered = ref('');
let controller;

async function initialize() {
  controller?.abort();
  controller = new AbortController();
  busy.value = true;
  error.value = '';
  try {
    const result = await billingCall('lifescc_billing_bootstrap', {}, controller.signal);
    const scope = billingBranches(result);
    if (!scope.branches.length) throw new Error('No permitted clinic branch is available for registration.');
    bootstrap.value = result;
    branches.value = scope.branches;
    branch.value = scope.selected;
  } catch (cause) {
    if (cause.name !== 'AbortError') error.value = cause.message || 'Could not load registration settings.';
  } finally {
    busy.value = false;
  }
}

function onRegistered(name) { registered.value = name; }
onMounted(initialize);
onBeforeUnmount(() => controller?.abort());
</script>

<template>
  <main class="client-registration-page">
    <header class="billing-list-head">
      <div><span class="billing-eyebrow">CLIENTS</span><h1>New Client Registration</h1><p>Register a client with a verified mobile number and attached PD form.</p></div>
      <button type="button" @click="router.push({ name: 'billing' })">Go to Billing</button>
    </header>
    <p v-if="busy" class="billing-loading" role="status">Loading permitted branches and practitioners…</p>
    <section v-else-if="error" class="billing-empty" role="alert"><h2>Registration is unavailable</h2><p>{{ error }}</p><button class="billing-primary" @click="initialize">Retry</button></section>
    <section v-else-if="registered" class="billing-empty" role="status"><span aria-hidden="true">✓</span><h2>Client registered</h2><p>Client ID: <strong>{{ registered }}</strong></p><button class="billing-primary" @click="router.push({ name: 'billing' })">Open Billing</button></section>
    <BillingRegistration v-else-if="bootstrap" :bootstrap="bootstrap" :branches="branches" :branch="branch" @busy-change="busy=$event" @registered="onRegistered" @cancel="router.push({ name: 'home' })" />
  </main>
</template>

<style scoped>
.client-registration-page{max-width:1120px;margin:0 auto;padding:8px 0 28px}
.client-registration-page .billing-list-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px}
.client-registration-page h1{margin:4px 0;font-size:clamp(24px,3vw,34px)}
.client-registration-page .billing-list-head p{margin:0;color:#60736b}
.client-registration-page button{font:inherit;cursor:pointer}
@media(max-width:650px){.client-registration-page .billing-list-head{align-items:flex-start;flex-direction:column}}
</style>
