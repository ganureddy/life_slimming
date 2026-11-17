import { computed, ref } from 'vue';
import { stockAction } from '../api/stock';

const snapshot = ref(null);
let inFlight = null;

export function useStockSuppliers() {
  const loading = ref(false);
  const error = ref('');
  const query = ref('');
  const rows = computed(() => (snapshot.value || []).filter(Boolean).filter(row => {
    const text = query.value.trim().toLowerCase();
    return !text || [row.name, row.supplier_name, row.supplier_group, row.email_id, row.mobile_no].some(value => String(value || '').toLowerCase().includes(text));
  }));
  async function load({ force = false } = {}) {
    if (!force && snapshot.value) return;
    if (!force && inFlight) return inFlight;
    loading.value = true; error.value = '';
    inFlight = stockAction('invoke', { method: 'frappe.client.get_list', args: { doctype: 'Supplier', fields: ['name','supplier_name','supplier_group','supplier_type','email_id','mobile_no','country','disabled','on_hold'], order_by: 'supplier_name asc', limit_page_length: 1000 } })
      .then(result => { snapshot.value = result.data || []; })
      .catch(cause => { error.value = cause.message || 'Could not load suppliers.'; })
      .finally(() => { loading.value = false; inFlight = null; });
    return inFlight;
  }
  return { loading, error, query, rows, load };
}
