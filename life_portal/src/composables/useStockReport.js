import { computed, ref } from 'vue';
import { stockAction } from '../api/stock';

const completed = new Map();
const pending = new Map();
const date = value => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;

export function useStockReport() {
  const today = new Date();
  const from = ref(date(new Date(today.getFullYear(), today.getMonth(), 1)));
  const to = ref(date(today));
  const query = ref('');
  const loading = ref(false);
  const error = ref('');
  const report = ref({ columns: [], result: [] });
  const columns = computed(() => report.value?.columns || []);
  const rows = computed(() => report.value?.result || []);
  const visibleRows = computed(() => {
    const text = query.value.trim().toLowerCase();
    return text ? rows.value.filter(row => Object.values(row).some(value => String(value ?? '').toLowerCase().includes(text))) : rows.value;
  });

  async function load({ force = false } = {}) {
    const key = `stock-balance:${from.value}:${to.value}`;
    if (!force && completed.has(key)) { report.value = completed.get(key); return; }
    if (!force && pending.has(key)) return pending.get(key);
    loading.value = true;
    error.value = '';
    const task = stockAction('invoke', { method: 'frappe.desk.query_report.run', args: { report_name: 'Stock Balance', filters: { from_date: from.value, to_date: to.value }, ignore_prepared_report: true } })
      .then(result => {
        const data = result.data || {};
        completed.set(key, data);
        report.value = data;
      })
      .catch(cause => { error.value = cause.message || 'Could not load Stock Balance.'; })
      .finally(() => { loading.value = false; pending.delete(key); });
    pending.set(key, task);
    return task;
  }

  function exportCsv() {
    const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const csv = [columns.value.map(column => quote(column.label || column.fieldname)).join(','), ...visibleRows.value.map(row => columns.value.map(column => quote(row[column.fieldname])).join(','))].join('\r\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    link.download = `stock-balance-${from.value}-to-${to.value}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  return { from, to, query, loading, error, columns, visibleRows, load, exportCsv };
}
