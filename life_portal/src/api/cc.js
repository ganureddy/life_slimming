import { request } from './http';
import { session } from '../lib/session';
export async function ccCall(method, args, signal) {
  const response = await request('life_slimming.api.server_scripts.' + method + '.run', { args, csrfToken: session.csrf_token, signal });
  if (response.message == null || response.message.ok === false || response.message.error) throw new Error(response.message?.error || 'No data returned. Please retry.');
  return response.message;
}
