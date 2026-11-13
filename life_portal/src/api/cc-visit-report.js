import { ccCall } from './cc';
import { session } from '../lib/session';
import { createReportLoader } from '../lib/cc-report-loader';
// Cache only within this portal session. Explicit Apply/refresh bypasses saved data;
// concurrent identical reads still share one network request.
export const requestVisitReport = createReportLoader(
  args => ccCall('life_cc_agent_marketing_data', args),
  () => [session.user, session.roles, session.csrf_token],
);
