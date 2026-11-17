import { computed, ref } from 'vue';
import { stockAction } from '../api/stock';

const snapshot = ref(null);
let inFlight = null;

export function useStockRequests() {
  const context = ref(null);
  const loading = ref(false);
  const error = ref('');
  const group = ref('all');
  const query = ref('');
  const page = ref(1);
  const busy = ref(false);
  const rows = computed(() => snapshot.value?.rows || []);
  const counts = computed(() => snapshot.value?.counts || {});
  const filteredRows = computed(() => {
    const text = query.value.trim().toLowerCase();
    return rows.value.filter(Boolean).filter(row => (!text || [row.name, row.title, row.set_warehouse, row.status, row.workflow_state].some(value => String(value || '').toLowerCase().includes(text))));
  });

  async function load({ force = false } = {}) {
    if (!force && snapshot.value && snapshot.value._group === group.value) return;
    if (!force && inFlight) return inFlight;
    loading.value = true;
    error.value = '';
    inFlight = (async () => {
      if (!context.value) context.value = await stockAction('get_context');
      const result = await stockAction('list_requests', {
        view: context.value?.is_ho ? 'ho' : 'branch',
        branch: context.value?.branch || '',
        group: group.value,
        page: page.value,
        page_size: 100,
        limit: 500,
      });
      snapshot.value = { ...result, _group: group.value };
    })().catch(cause => { error.value = cause.message || 'Could not load stock requests.'; }).finally(() => { loading.value = false; inFlight = null; });
    return inFlight;
  }

  async function decide(row, decision, remarks = '') {
    if (!row?.name) return;
    busy.value = true;
    error.value = '';
    try {
      if (decision === 'approve') {
        const approvals = (row.items || []).map(item => ({
          item_code: item.item_code,
          material_request_item: item.name,
          approved_qty: Number(item.custom_approved_qty ?? item.qty ?? 0),
        }));
        await stockAction('approve_request', { request_name: row.name, approvals, remarks });
      } else {
        await stockAction('reject_request', { request_name: row.name, remarks });
      }
      snapshot.value = null;
      await load({ force: true });
    } catch (cause) {
      error.value = cause.message || `Could not ${decision} the material request.`;
    } finally { busy.value = false; }
  }

  return { context, loading, error, group, query, page, busy, rows, counts, filteredRows, load, decide };
}
