import { request } from './http';
import { session } from '../lib/session';
export async function ccCore(action, args = {}, signal) {
  const response = await request('life_cc_core', { args: { action, ...args }, csrfToken: session.csrf_token, signal });
  if (response.message?.conflict) return response.message;
  if (!response.message?.ok) throw new Error(response.message?.error || 'The CC request could not be completed.');
  return response.message;
}
