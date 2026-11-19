import { computed, ref } from 'vue';
import { stockAction } from '../api/stock';

const cache = new Map();
const pending = new Map();

/** Shared dashboard read model. It is deliberately independent from tab UI. */
export function useStockDashboardOverview() {
  const context = ref(null);
  const bins = ref([]);
  const loading = ref(false);
  const error = ref('');
  const warehouse = ref('');
  const category = ref('');
  const status = ref('');

  const warehouses = computed(() => (context.value?.allowed_warehouses || []).map(row => typeof row === 'string' ? row : row?.name).filter(Boolean));
  const validBins = computed(() => bins.value.filter(row => row && typeof row === 'object'));
  const categories = computed(() => [...new Set(validBins.value.map(row => row.item_group).filter(Boolean))].sort());
  const visibleBins = computed(() => validBins.value.filter(row =>
    (!warehouse.value || row.warehouse === warehouse.value) &&
    (!category.value || row.item_group === category.value) &&
    (!status.value || (status.value === 'Zero Stock' ? Number(row.actual_qty) <= 0 : status.value === 'Low Stock' ? Number(row.actual_qty) > 0 && Number(row.actual_qty) <= 5 : Number(row.actual_qty) > 5)),
  ));
  const metrics = computed(() => ({
    items: new Set(validBins.value.map(row => row.item_code).filter(Boolean)).size,
    quantity: validBins.value.reduce((total, row) => total + Number(row.actual_qty || 0), 0),
    zero: validBins.value.filter(row => Number(row.actual_qty || 0) <= 0).length,
    low: validBins.value.filter(row => Number(row.actual_qty || 0) > 0 && Number(row.actual_qty || 0) <= 5).length,
  }));

  async function load({ force = false } = {}) {
    const key = 'stock-dashboard-overview';
    if (!force && cache.has(key)) {
      ({ context: context.value, bins: bins.value } = cache.get(key));
      return;
    }
    if (!force && pending.has(key)) return pending.get(key);
    loading.value = true;
    error.value = '';
    const task = Promise.all([
      stockAction('get_context'),
    ]).then(async ([loadedContext]) => {
      const allowed = (loadedContext.allowed_warehouses || []).map(row => typeof row === 'string' ? row : row?.name).filter(Boolean);
      const [binRows, itemRows] = await Promise.all([
        stockAction('invoke', { method: 'frappe.client.get_list', args: { doctype: 'Bin', fields: ['item_code', 'warehouse', 'actual_qty', 'projected_qty', 'valuation_rate'], filters: { warehouse: ['in', allowed] }, limit_page_length: 5000 } }),
        stockAction('invoke', { method: 'frappe.client.get_list', args: { doctype: 'Item', fields: ['name', 'item_name', 'item_group'], filters: { disabled: 0, is_stock_item: 1 }, limit_page_length: 5000 } }),
      ]);
      const itemByCode = new Map((itemRows.data || []).filter(row => row && row.name).map(row => [row.name, row]));
      const snapshot = { context: loadedContext || {}, bins: (binRows.data || []).filter(row => row && row.item_code).map(row => ({ ...row, ...(itemByCode.get(row.item_code) || {}) })) };
      cache.set(key, snapshot);
      context.value = snapshot.context;
      bins.value = snapshot.bins;
    }).catch(cause => { error.value = cause.message || 'Could not load the stock dashboard.'; }).finally(() => { loading.value = false; pending.delete(key); });
    pending.set(key, task);
    return task;
  }

  return { context, bins, loading, error, warehouse, category, status, warehouses, categories, visibleBins, metrics, load };
}
