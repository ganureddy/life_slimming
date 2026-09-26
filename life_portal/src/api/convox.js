import { request } from './http';
import { session } from '../lib/session';

async function call(action, args = {}, signal) {
  const body = await request(`life_slimming.api.convox.${action}`, {
    args, csrfToken: session.csrf_token, signal,
  });
  return body.message;
}
export const convoxApi = {
  config: (signal) => call('config', {}, signal),
  widgetSession: (signal, manual = false) => call('widget_session', { manual: manual ? 1 : 0 }, signal),
  callTarget: (lead_id, signal) => call('call_target', { lead_id }, signal),
  poll: (after, signal) => call('poll', { after }, signal),
  callLead: (lead_id, request_id, signal) => call('click_to_call', { lead_id, request_id }, signal),
};
export const CONVOX_ORIGIN = 'https://lifeslimming.deepijatel.in';
export function createRequestId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
}

// Keep uncertain requests tied to their lead even when the agent navigates away.
export function createCallRequests(makeId = createRequestId) {
  const pending = new Map();
  return {
    forLead(lead) {
      if (!pending.has(lead)) pending.set(lead, makeId());
      return pending.get(lead);
    },
    settle(lead, id, status) {
      if (status && status !== 'UNKNOWN' && pending.get(lead) === id) pending.delete(lead);
    },
  };
}
export function validWidgetUrl(value) {
  try {
    const url = new URL(value);
    return url.origin === CONVOX_ORIGIN && url.pathname === '/ConVoxCCS/ExternalIndex'
      && !url.username && !url.password && !url.hash;
  } catch { return false; }
}
export function isDashboardMessage(event, frame, origin) {
  const data = event.data;
  const validLead = typeof data?.lead_id === 'string' && data.lead_id.length > 0 && data.lead_id.length <= 140;
  return Boolean(frame && event.origin === origin && event.source === frame.contentWindow
    && ['life-convox-select', 'life-convox-open', 'life-convox-call'].includes(data?.type)
    && (data.lead_id === undefined || validLead)
    && (data.type !== 'life-convox-call' || (validLead
      && typeof data.request_id === 'string' && /^[a-f0-9]{32}$/.test(data.request_id))));
}
