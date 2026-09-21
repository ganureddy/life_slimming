<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import billingSource from "../data/billingV2LiveSource.json";
import { apiUrl, apiCredentials } from "../api/config";
import endpoints from "../api/endpoints.json";
import { session } from "../lib/session";

const host = ref(null);
const loadError = ref("");
const injected = [];

const legacyToId = {
  "apply_invoice_discount_NET_FINAL_V2": "apply_invoice_discount_net_final_v2",
  "create_discount_approval_request": "create_discount_approval_request",
  "create_multiple_discount_approval_requests_v2": "create_multiple_discount_approval_requests_v2",
  "lifescc.billing.bootstrap": "lifescc_billing_bootstrap",
  "lifescc.billing.collect_payment_v4": "lifescc_billing_collect_payment_v4",
  "lifescc.billing.collections_report": "lifescc_billing_collections_report",
  "lifescc.billing.create_client": "lifescc_billing_create_client",
  "lifescc.billing.create_plan_and_invoice_TEST": "lifescc_billing_create_plan_and_invoice_test",
  "lifescc.billing.lead_lookup": "lifescc_billing_lead_lookup",
  "lifescc.billing.submit_invoice": "lifescc_billing_submit_invoice",
  "validate_coupon": "validate_coupon",
  "life_stock_fast_requests": "life_stock_fast_requests",
};

function csrfToken() {
  return session.csrf_token || window.csrf_token || "";
}

async function invoke(method, args = {}, type = "POST") {
  const id = legacyToId[method];
  const resolved = id && endpoints[id] ? endpoints[id] : method;
  const response = await fetch(apiUrl("/api/method/" + resolved), {
    method: type === "GET" ? "GET" : "POST",
    credentials: apiCredentials(),
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": csrfToken(),
    },
    body: type === "GET" ? undefined : JSON.stringify(args || {}),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.exc_type) {
    const error = new Error(body.message || body.exception || "Billing request failed");
    error.response = body;
    throw error;
  }
  return body;
}

function installFrappeBridge() {
  const existing = window.frappe || {};
  existing.session = existing.session || { user: session.user || "Guest" };
  existing.csrf_token = existing.csrf_token || csrfToken();
  existing.datetime = existing.datetime || {
    get_today: () => new Date().toISOString().slice(0, 10),
    now_date: () => new Date().toISOString().slice(0, 10),
    add_days: (value, days) => {
      const date = new Date(value + "T00:00:00");
      date.setDate(date.getDate() + Number(days || 0));
      return date.toISOString().slice(0, 10);
    },
  };
  existing.boot = existing.boot || { sysdefaults: { date_format: "dd-mm-yyyy" } };
  existing.ready = existing.ready || ((callback) => callback());
  existing.call = function call(options) {
    const request = typeof options === "string" ? { method: options } : options || {};
    const promise = invoke(request.method, request.args || {}, request.type || "POST");
    promise.then(
      (body) => request.callback && request.callback(body),
      (error) => request.error && request.error(error),
    );
    return promise;
  };
  window.frappe = existing;
}

function extractBillingApp() {
  const parsed = new DOMParser().parseFromString(billingSource.html, "text/html");
  const app = parsed.querySelector("#app");
  if (!app) throw new Error("The exported Billing #app container was not found");
  app.id = "billing-v2-app";
  app.querySelectorAll("input, textarea").forEach((element) => {
    element.removeAttribute("value");
    if (element.tagName === "TEXTAREA") element.textContent = "";
  });
  return app.outerHTML;
}

function adaptCode(code) {
  return code
    .replaceAll("getElementById('app')", "getElementById('billing-v2-app')")
    .replaceAll('getElementById("app")', 'getElementById("billing-v2-app")');
}

async function mountBilling() {
  installFrappeBridge();
  host.value.innerHTML = extractBillingApp();

  for (const block of billingSource.css) {
    const style = document.createElement("style");
    style.dataset.lifeBillingV2 = String(block.index);
    style.textContent = block.code
      .replaceAll("#app", "#billing-v2-app");
    document.head.appendChild(style);
    injected.push(style);
  }

  await nextTick();
  for (const block of billingSource.javascript) {
    const script = document.createElement("script");
    script.dataset.lifeBillingV2 = String(block.index);
    script.textContent = adaptCode(block.code);
    document.body.appendChild(script);
    injected.push(script);
  }
}

onMounted(() => {
  mountBilling().catch((error) => {
    loadError.value = error.message || "Billing could not be loaded";
  });
});

onBeforeUnmount(() => {
  for (const element of injected) element.remove();
});
</script>

<template>
  <section class="billing-compat-page">
    <div v-if="loadError" class="billing-load-error">
      <strong>Billing could not be loaded.</strong>
      <span>{{ loadError }}</span>
    </div>
    <div ref="host"></div>
  </section>
</template>

<style scoped>
.billing-compat-page{margin:-30px -32px -48px;min-height:calc(100dvh - var(--header-height));background:#f3faf6}.billing-load-error{margin:24px;padding:18px;display:grid;gap:5px;color:#8f241f;background:#fff0ef;border:1px solid #efc4c1;border-radius:10px}.billing-load-error span{font-size:12px}@media(max-width:980px){.billing-compat-page{margin:-25px}}@media(max-width:600px){.billing-compat-page{margin:-22px -16px}}
</style>
