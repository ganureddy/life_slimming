// Each CRM page has its own path; the parent shell owns shared data and requests.
export const ccTabs = [
  { view: 'dashboard', label: 'CC Dashboard', icon: '◎' },
  { view: 'testing', label: 'Lead Updates', icon: '🧪' },
  { view: 'queue', label: 'My Lead Queue', icon: '📋' },
  { view: 'followup', label: 'Lead Follow-Up Form', icon: '📞' },
  { view: 'create', label: 'Create Lead', icon: '➕' },
  { view: 'assign', label: 'Assign Leads', icon: '🔀', manager: true },
  { view: 'duplicates', label: 'Duplicate Leads', icon: '🧬', manager: true },
  { view: 'worksheet', label: 'My Worksheet', icon: '📊' },
  { view: 'distribution', label: 'Lead Distribution', icon: '🔀', mover: true },
  { view: 'tl', label: 'TL Control Panel', icon: '👥', manager: true },
  { view: 'reports', label: 'CC Reports', icon: '📈' },
  { view: 'scripts', label: 'Call Scripts', icon: '💬' },
  { view: 'faq', label: 'FAQ / Knowledge Base', icon: '❓' },
  { view: 'treatments', label: 'Treatment Guide', icon: '💉' },
  { view: 'objections', label: 'Objection Handling', icon: '🛡️' },
  { view: 'branches', label: 'Branch Directory', icon: '🏥' },
  { view: 'doctors', label: 'Doctor Directory', icon: '👨‍⚕️' },
];

const pagePaths = { dashboard:'', testing:'updates', queue:'queue', followup:'follow-up', create:'create', assign:'assign', duplicates:'duplicates', worksheet:'worksheet', distribution:'distribution', tl:'team-lead', reports:'reports', scripts:'scripts', faq:'faq', treatments:'treatments', objections:'objections', branches:'branches', doctors:'doctors' };
export function ccPagePath(view) { return pagePaths[view] ?? ''; }
export function isCcRoute(route) { return route.meta?.ccView != null || ['leads','leads-native'].includes(route.name); }
export function ccViewOfRoute(route) { return route.meta?.ccView || (typeof route.query?.view === 'string' ? route.query.view : 'dashboard'); }
export function ccRoute(view = 'dashboard', query = {}) {
  if (!Object.hasOwn(pagePaths, view)) view = 'dashboard';
  const { view: _oldView, lead, ...rest } = query;
  return { name:view==='dashboard'?'leads':'cc-leads-'+view, ...(view==='followup'&&lead?{params:{leadId:lead}}:{}), query:rest };
}
