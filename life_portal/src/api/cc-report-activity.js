import { request } from './http';
import { session } from '../lib/session';
import { createReportLoader } from '../lib/cc-report-loader';
// The embedded report tab and the standalone Agent 360 share this read cache.
export const requestReportActivity = createReportLoader(
  async args => (await request('life_slimming.api.cc_report_activity.run', { args, csrfToken: session.csrf_token })).message,
  () => [session.user, session.roles, session.csrf_token],
  60000,
);
