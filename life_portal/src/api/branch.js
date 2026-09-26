import { request } from './http';
import { session } from '../lib/session';

// The browser calls our session-bound gateway; ERP cookies never reach JavaScript.
export async function branchApi(action, args = {}, signal) {
  if (!['connect', 'disconnect', 'dashboard'].includes(action)) throw new Error('Unknown branch API');
  const { message } = await request(`life_slimming.api.remote_erp.${action}`, {
    args, csrfToken: session.csrf_token, signal,
  });
  if (!message || typeof message !== 'object') throw new Error('Unexpected server response. Please retry.');
  return message;
}
