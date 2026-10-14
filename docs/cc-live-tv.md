# CC Live TV

Open `/life_portal/native/cc-live-tv` or use **Live TV** in the native CC dashboard header. The reusable component is `life_portal/src/components/cc/CCLiveTV.vue`.

Click **Enable sound** once per screen session to unlock browser audio. Each event type has its own chime. Fullscreen works with the button or F; Escape exits browser fullscreen. Animations respect reduced-motion settings.

The authenticated, read-only `life_slimming.api.cc_live_tv.snapshot` endpoint refreshes five seconds after each completed request. It applies the leads module policy and the CC lead queue's manager/owner scope. Agents see their own leads; System Manager, Sales Manager and Call Center Export see all leads. No guest access or sample data is enabled.

Counting rules:

- Leads: creation date, in the site's timezone.
- Booked: leads with a current scheduled appointment in the period, excluding cancelled appointments.
- Visited (formerly Walk-ins): those scheduled leads whose status is visited, using the existing CC visit-report status rules.
- Today means the site calendar day. The monthly cycle runs from the 6th through the next month’s 5th, inclusive (before the 6th, it starts in the previous month). These are current lead snapshots, not a historical count of every appointment or an arrival timestamp report.
- Unassigned leads contribute to totals but do not occupy an agent podium. Ties use visited-booked counts, appointment bookings, leads, then agent ID.

The first successful load establishes a silent baseline. Subsequent snapshots announce new leads, booking/reschedule changes and transitions to visited. Changed leaders trigger a celebration after a walk-in. Existing activity is not replayed on page reload. Events are observed snapshot differences; intermediate changes between polls cannot be reconstructed. The visible feed keeps seven events; the alert queue keeps the latest twelve to avoid prolonged alerts after bulk updates or reconnects. No persistent event history is created.

Errors show a connection warning and retain the last snapshot; authentication/permission failures clear it. All timers, requests and audio resources are released on leaving the component. Normal portal session expiry remains in effect.

Validation: `node --test life_portal/tests/cc-live-tv.test.mjs`, `python3 life_portal/tests/test_cc_live_tv.py`, and `npm run build --prefix life_portal`. A signed-in production browser check is still needed to verify site data and audible playback on the target TV.

Agent podium portraits use the lead owner’s User `user_image` field. Missing or inaccessible photos fall back to initials.

- Visited Booked: the subset of visited leads resolving to `Visited-BKD`, counted by scheduled appointment date for today and the 6th–5th monthly cycle. Displayed in the daily totals and both agent podiums.

The v2 design follows the supplied `life-cc-tv-v2 (3).html`: gold frame, compact podiums, weekly ranking band, breaking highlights, idle roster, volume slider (M toggles sound), and booking confetti. It uses authenticated snapshots; demo data, random events, and unauthenticated postMessage input are not imported.

Weekly visits use Monday–Sunday in the site timezone, including prior-month appointments when the week crosses a month boundary. Target: 35 / 4 = 8.75 visits per week, as in the supplied design. Percent bars cap at 100%. Agent lists include enabled User owners represented in the scoped snapshot, not every ERP User. Disabled or missing users are excluded from podiums, the roster, weekly rankings, highlights, and named alerts; their lead activity remains in totals. User enabled state is refreshed on every poll, and disabling an owner clears their pending/displayed activity alerts. Weekly ties use agent ID; the weekly target does not affect rank. After 40 seconds without observed activity, the right panel displays these agents, rotating every eight seconds (ten rows, or eight when a waiting alert is present).

Waiting alerts use today's leads at least ten minutes old with an explicit zero `custom_call_count` and empty `custom_last_call_time`. Scheduled/visited and converted/lost/do-not-contact leads are excluded. Missing fields do not imply no calls. The label is “No call recorded”: these fields record CC follow-ups, not definitive telephony dial events. Alerts clear after the next snapshot records a call; audio reminders are at most once per two minutes, only when sound is enabled and the connection is fresh.

Highlights use the reference thresholds: five visits/day, five appointments/day, fifty visits/month, or at least a 50% visited-booked ratio with two visits. High-package highlights are omitted because the TV snapshot has no verified package amount attribution. Sound still needs an initial user click under browser autoplay rules.

Browser verification: `node life_portal/tests/cc-live-tv.browser.cjs` with Vite on port 5178 and an isolated Chrome debugger on port 9230. Tests mock all API data and cover totals, roster pagination, waiting-alert removal, screen scaling, and clearing data after permission denial.

TV latest-lead and waiting cards, activity entries and lead alerts display the raw Lead `custom_visit_status` as **Visit Status**, or **Not set** when empty. Appointment status remains separate; counting rules are unchanged.

Visit Status breakdowns also appear in today’s overall totals, daily/monthly podiums, each agent ranking row, weekly rankings and champion alerts. Each raw `custom_visit_status` value shows its lead count; empty values count as Not set. Periods use appointment date, falling back to creation for unscheduled leads. Roster pages contain six agents with a waiting alert or eight otherwise to fit the additional field.

Visit Status is now a numeric metric tile/column matching the other metrics in totals, podiums and agent rankings (and a count in weekly rankings). It counts leads explicitly marked Visited in `custom_visit_status`, using scheduled date or creation for unscheduled leads. An appointment still marked Booked no longer hides an explicit Visit Status of Visited when calculating visits or announcing a visit. This replaces the textual aggregate breakdown in those views.
