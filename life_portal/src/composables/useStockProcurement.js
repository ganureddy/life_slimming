import { computed, ref } from 'vue';
import { stockAction } from '../api/stock';

const snapshot = ref(null);
let inFlight = null;

export function useStockProcurement() {
  const loading = ref(false);
  const error = ref('');
  const query = ref('');
  const documents = computed(() => snapshot.value || {});
  const matches = doctype => (documents.value[doctype] || []).filter(Boolean).filter(row => {
    const text = query.value.trim().toLowerCase();
    return !text || [row.name, row.supplier, row.supplier_name, row.status, row.workflow_state].some(value => String(value || '').toLowerCase().includes(text));
  });

  async function load({ force = false } = {}) {
    if (!force && snapshot.value) return;
    if (!force && inFlight) return inFlight;
    loading.value = true;
    error.value = '';
    const specs = {
      'Purchase Order': ['name', 'transaction_date', 'supplier', 'supplier_name', 'status', 'workflow_state', 'docstatus', 'grand_total', 'currency', 'per_received'],
      'Purchase Receipt': ['name', 'posting_date', 'supplier', 'supplier_name', 'status', 'docstatus', 'grand_total', 'currency'],
      'Purchase Invoice': ['name', 'posting_date', 'supplier', 'supplier_name', 'status', 'docstatus', 'grand_total', 'outstanding_amount', 'currency'],
    };
    inFlight = Promise.all(Object.entries(specs).map(async ([doctype, fields]) => [doctype, await stockAction('invoke', { method: 'frappe.client.get_list', args: { doctype, fields, order_by: 'modified desc', limit_page_length: 500 } })]))
      .then(results => { snapshot.value = Object.fromEntries(results.map(([doctype, result]) => [doctype, result.data || []])); })
      .catch(cause => { error.value = cause.message || 'Could not load purchasing documents.'; })
      .finally(() => { loading.value = false; inFlight = null; });
    return inFlight;
  }

  return { loading, error, query, documents, matches, load };
}
