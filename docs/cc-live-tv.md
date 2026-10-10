# CC Live TV

Open `/life_portal/native/cc-live-tv` or use **Live TV** in the native CC dashboard header. The reusable component is `life_portal/src/components/cc/CCLiveTV.vue`.

Click **Enable sound** once per screen session to unlock browser audio. Each event type has its own chime. Fullscreen works with the button or F; Escape exits browser fullscreen. Animations respect reduced-motion settings.

The authenticated, read-only `life_slimming.api.cc_live_tv.snapshot` endpoint refreshes five seconds after each completed request. It applies the leads module policy and the CC lead queue's manager/owner scope. Agents see their own leads; System Manager, Sales Manager and Call Center Export see all leads. No guest access or sample data is enabled.

Counting rules:

- Leads: creation date, in the site's timezone.
- Booked: leads with a current scheduled appointment in the period, excluding cancelled appointments.
- Visited (formerly Walk-ins): those scheduled leads whose status is visited, using the existing CC visit-report status rules.
- Today and month mean the site calendar day and calendar month. These are current lead snapshots, not a historical count of every appointment or an arrival timestamp report.
- Unassigned leads contribute to totals but do not occupy an agent podium. Ties use bookings, leads, then agent ID.

The first successful load establishes a silent baseline. Subsequent snapshots announce new leads, booking/reschedule changes and transitions to visited. Changed leaders trigger a celebration after a walk-in. Existing activity is not replayed on page reload. Events are observed snapshot differences; intermediate changes between polls cannot be reconstructed. The visible feed keeps seven events; the alert queue keeps the latest twelve to avoid prolonged alerts after bulk updates or reconnects. No persistent event history is created.

Errors show a connection warning and retain the last snapshot; authentication/permission failures clear it. All timers, requests and audio resources are released on leaving the component. Normal portal session expiry remains in effect.

Validation: `node --test life_portal/tests/cc-live-tv.test.mjs`, `python3 life_portal/tests/test_cc_live_tv.py`, and `npm run build --prefix life_portal`. A signed-in production browser check is still needed to verify site data and audible playback on the target TV.

Agent podium portraits use the lead owner’s User `user_image` field. Missing or inaccessible photos fall back to initials.

- Visited Booked: the subset of visited leads resolving to `Visited-BKD`, counted by scheduled appointment date for today and the calendar month. Displayed in the daily totals and both agent podiums.
