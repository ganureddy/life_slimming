<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import billingSource from "../data/billingV2LiveSource.json";
import { apiUrl, apiCredentials } from "../api/config";
import endpoints from "../api/endpoints.json";
import { session } from "../lib/session";
import { indiaStamp } from "../lib/cc";
import { beginLoading } from "../lib/loading";
const pendingLoads = new Set();
let billingMounted = false;
import billingPolish from "../styles/billing.css?inline";

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
  // Individual API requests already have local progress states. Showing the
  // full-screen route loader for every request hides the page during searches
  // and competing bootstrap calls; reserve it for the first bootstrap call.
  const isBootstrap = method === "lifescc.billing.bootstrap" && !billingMounted;
  const finish = isBootstrap ? beginLoading("Loading billing") : null;
  if (finish) pendingLoads.add(finish);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 45000);
  try {
  const response = await fetch(apiUrl("/api/method/" + resolved), {
    method: type === "GET" ? "GET" : "POST",
    credentials: apiCredentials(),
    signal: controller.signal,
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
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Billing request timed out. Check your connection and retry.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
    if (finish) { finish(); pendingLoads.delete(finish); }
  }
}

function installFrappeBridge() {
  const existing = window.frappe || {};
  existing.session = existing.session || { user: session.user || "Guest" };
  existing.csrf_token = existing.csrf_token || csrfToken();
  existing.datetime = {
    ...existing.datetime,
    get_today: () => indiaStamp().slice(0, 10),
    now_date: () => indiaStamp().slice(0, 10),
    now_datetime: () => indiaStamp(),
    add_days: (value, days) => {
      const date = new Date(value + "T12:00:00Z");
      date.setUTCDate(date.getUTCDate() + Number(days || 0));
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
  // Notifications need to escape the billing app's isolated stacking context.
  // Keep them in the Vue page but mount at the document root.
  const alerts = app.querySelector("#alert-stack");
  if (alerts) alerts.dataset.billingToastHost = "true";
  app.querySelectorAll(".topbar > .logo-box, .topbar > div:has(> .brand)").forEach(element => element.remove());
  app.querySelector("#clock")?.setAttribute("hidden", "");
  app.querySelectorAll("input, textarea").forEach((element) => {
    element.removeAttribute("value");
    if (element.tagName === "TEXTAREA") element.textContent = "";
  });
  const labels = {
    q: "Search clients by name, mobile number or client ID",
    "mini-q": "Search another client",
    scope: "Branch",
    "rec-q": "Search recent bills",
    "rec-status": "Invoice status",
    "rec-from": "Recent bills from date",
    "rec-to": "Recent bills to date",
  };
  for (const [id, label] of Object.entries(labels)) {
    app.querySelector(`#${id}`)?.setAttribute("aria-label", label);
  }
  return app.outerHTML;
}

function adaptCode(code) {
  return code
    // The server applies the fixed package price without stacking coupons or
    // staff discounts. Keep the exported preview consistent with that amount.
    .replace("var net=subRaw-couponAmt-disc-pkgDisc;", "if(pkg>0){couponAmt=0;disc=0;pct=0;} var net=subRaw-couponAmt-disc-pkgDisc;")
    .replace("var isPkg=parseFloat(BILL.pkg_price||0)>0;", "var isPkg=parseFloat(BILL.pkg_price||0)>0; var couponSection=_g('bl-coupon-sec'); if(couponSection)couponSection.style.display=isPkg?'none':''; if(isPkg){COUPON_AMOUNT=0;COUPON_PCT=0;COUPON_APPLIED='';}")
    .replaceAll("document.body.appendChild(", "document.querySelector('.billing-compat-page').appendChild(")
    .replaceAll("getElementById('app')", "getElementById('billing-v2-app')")
    .replaceAll('getElementById("app")', 'getElementById("billing-v2-app")');
}

// The exported page includes global resets and classes shared with the portal.
// Scope parsed CSS rules, including nested media rules, but leave keyframes alone.
function scopedBillingCss(code) {
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(code.replaceAll("#app", "#billing-v2-app"));
  function scope(rules) {
    for (const rule of rules) {
      if (rule.type === CSSRule.STYLE_RULE) {
        // Toasts are mounted at document.body so they can layer above the
        // portal header; keep their legacy visual rules global as well.
        if (rule.selectorText.split(",").some((selector) => /\.alert(?:\b|[-.#:[\s])/i.test(selector))) continue;
        const selector = rule.selectorText
          .replaceAll(":root", ".billing-compat-page")
          .replace(/(^|[\s>+~,(])(?:html|body)(?=$|[\s>+~.#:[,)])/g, "$1.billing-compat-page");
        // Match the wrapper itself as well as descendants (for root variables).
        rule.selectorText = `:is(.billing-compat-page, .billing-compat-page *):is(${selector})`;
      } else if (rule.cssRules && rule.type !== CSSRule.KEYFRAMES_RULE) {
        scope(rule.cssRules);
      }
    }
  }
  scope(sheet.cssRules);
  return Array.from(sheet.cssRules, (rule) => rule.cssText).join("\n");
}

async function mountBilling() {
  installFrappeBridge();
  host.value.innerHTML = extractBillingApp();
  const alertStack = host.value.querySelector("#alert-stack");
  if (alertStack) {
    alertStack.dataset.billingToastHost = "true";
    document.body.appendChild(alertStack);
    injected.push(alertStack);
  }
  billingMounted = true;


  for (const block of billingSource.css) {
    const style = document.createElement("style");
    style.dataset.lifeBillingV2 = String(block.index);
    style.textContent = scopedBillingCss(block.code);
    document.head.appendChild(style);
    injected.push(style);
  }

  const polish = document.createElement("style");
  polish.textContent = billingPolish;
  document.head.appendChild(polish);
  injected.push(polish);

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
  billingMounted = false;
  for (const finish of pendingLoads) finish();
  pendingLoads.clear();
  document.querySelector("body > #alert-stack")?.remove();
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
