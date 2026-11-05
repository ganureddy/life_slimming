# CC ROASTER

Added `/life_portal/cc-roster`, accessible from the portal CC menu and the embedded CC dashboard sidebar. It uses the existing `Ho CC` branch (verified in ERP Portal), active Employee records and standard HR Shift Assignment records. No new DocType or copied roster data is needed.

- Week: Monday–Sunday, previous/next week, Today and date selection.
- Month: complete month calendar and per-employee planned-work, week-off, unplanned, submitted-attendance and leave-day summaries.
- Employee and department filters apply to both the calendar and summary.
- Submitted active shifts include overlapping date ranges and assignments without an end date. Conflicts remain visible rather than hiding a shift.
- Approved leave and submitted Attendance provide badges. Missing attendance is not classified as absence. Leave counts represent calendar dates with approved leave, not payroll leave balances or half-day units.
- Only Call Center Export and System Manager can assign, change or clear shifts. All other roles with CC access are view-only, even if they have HR permissions. Shift editing uses existing Shift Types and standard HR insert/submit/cancel hooks through this explicitly role-gated, Ho CC-only endpoint. Cancelled records are retained.
- Each edit checks the assignment ID and modified timestamp, and serializes roster edits per employee. Multi-day assignments must be maintained through HR so a single-day change cannot inadvertently cancel the entire range.

The new `life_slimming.api.cc_roster` endpoints require access to the CC lead module. Reads are explicitly scoped to active Ho CC employees and return only roster identity, planned shifts and attendance/leave status; they do not expose salary, personal contact details, leave reasons or raw punches. Writes cannot target employees in other branches or inactive employees and use the explicit roster editor roles instead of general HR document permissions.

The live legacy ERP Web Page was not edited. The portal inserts the new CC link when loading its existing embedded dashboard. Deploy the app Python and built frontend together through the usual deployment process. Users without Call Center Export or System Manager can only view the roster. No general HR roles or permissions were assigned as part of this change.

Validation: 13 Python boundary/write tests, two JavaScript calendar/summary tests and a successful Vue production build. Existing Vite bundle-size and mixed-import warnings remain. No live employee assignments were changed during testing.
