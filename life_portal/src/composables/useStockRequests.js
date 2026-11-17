import { computed, ref } from 'vue';
import { stockAction } from '../api/stock';

// Shared snapshot across mounted request tabs; do not share per-tab UI state.
const snapshots = new Map();
const pending = new Map();

export function useStockRequests() {
  const context = ref(null);
  const loading = ref(false);
  const error = ref('');
  const group = ref('all');
  const query = ref('');
  const page = ref(1);
  const busy = ref(false);
  const snapshot = ref(null);
  const rows = computed(() => snapshot.value?.rows || []);
  const counts = computed(() => snapshot.value?.counts || {});
  const filteredRows = computed(() => {
    const text = query.value.trim().toLowerCase();
    return rows.value.filter(Boolean).filter(row =>
      !text || [row.name, row.title, row.set_warehouse, row.status, row.workflow_state]
        .some(value => String(value || '').toLowerCase().includes(text))
    );
  });

  let sequence = 0;
  async function load({ force = false } = {}) {
    const currentSequence = ++sequence;
    loading.value = true;
    error.value = '';
    try {
      if (!context.value) context.value = await stockAction('get_context');
      const payload = {
        view: context.value?.is_ho ? 'ho' : 'branch',
        branch: context.value?.branch || '',
        group: group.value,
        page: page.value,
        page_size: 100,
        limit: 500,
      };
      const key = JSON.stringify(payload);
      if (!force && snapshots.has(key)) {
        if (currentSequence === sequence) snapshot.value = snapshots.get(key);
        return;
      }
      if (!pending.has(key)) {
        const task = stockAction('list_requests', payload)
          .then(result => { snapshots.set(key, { ...result, _group: payload.group }); return snapshots.get(key); })
          .finally(() => { if (pending.get(key) === task) pending.delete(key); });
        pending.set(key, task);
      }
      const result = await pending.get(key);
      if (currentSequence === sequence) snapshot.value = result;
    } catch (cause) {
      if (currentSequence === sequence) error.value = cause.message || 'Could not load stock requests.';
    } finally {
      if (currentSequence === sequence) loading.value = false;
    }
  }

  async function decide(row, decision, remarks = '') {
    if (!row?.name || busy.value) return;
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
      snapshots.clear();
      await load({ force: true });
    } catch (cause) {
      error.value = cause.message || `Could not ${decision} the material request.`;
    } finally {
      busy.value = false;
    }
  }

  return { context, loading, error, group, query, page, busy, rows, counts, filteredRows, load, decide };
}