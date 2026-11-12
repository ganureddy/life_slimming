// One modal is owned by PortalLayout; callers keep their current page and draft.
export function openConvoxHistory(leadId) {
  if (typeof leadId !== 'string' || !leadId || leadId.length > 140) return;
  window.dispatchEvent(new CustomEvent('life-convox-history-open', { detail: { leadId } }));
}
