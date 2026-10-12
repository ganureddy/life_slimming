// Dashboard presentation groups; these do not rewrite saved Lead stages.
export function ccDashboardGroup(row) {
  // A specific sub-status wins conflicts, including outcomes outside these groups.
  // Legacy pages expose Lead.status as portalStatus and CC Stage as status.
  const values = [row.subStatus, row.custom_cc_sub_status, row.portalStatus, row.status];
  for (const value of values) {
    const status = String(value || '').trim().toLowerCase().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ');
    if (['call back', 'callback', 'callback: scheduled', 'get back'].includes(status)) return 'followup';
    if (['not responding', 'no response', 'not response', 'switch off', 'not reachable'].includes(status)) return 'norespnotreach';
    if (['not in service', 'invalid number', 'not enquired', 'wrong no', 'wrong no.', 'wrong number', 'not interested', 'tna'].includes(status)) return 'invalid';
    if (['nid', 'distance', 'non local', 'nonlocal'].includes(status)) return 'nid';
    // Only empty/default values may fall back to the saved Lead status.
    if (status && status !== 'lead') return '';
  }
  return '';
}
