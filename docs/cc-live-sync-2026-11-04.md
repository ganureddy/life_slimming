# CC live source sync — 4 November 2026

Source: ERP Portal Web Page `cc-new-dash`, modified `2026-11-04 15:50:33.674373`.

The maintained legacy snapshot now contains the live HTML, CSS and dashboard script extracted from the standalone bootstrap wrapper, plus the newly appended V18 mobile-call popup. The local optional-read-access guard is preserved. The standalone bootstrap wrapper is excluded because the portal supplies its own runtime.

The Vue CC dashboard also displays the agent's live mobile call, supports opening the lead, remembers the automatic-opening preference, pauses polling in hidden tabs and cancels polling when the component unmounts. It calls the existing authenticated `life_cc_mobile_v18` Server Script with `action=live`; no new server installation is required for this feature.

## Server Script review

ERP Portal returned 15 enabled `cc_*` API scripts. Two enabled documents register **the same `cc_update_lead` method**:

- `cc_update_lead`, modified 3 October 2026.
- `CC update lead Testing kavya`, modified 29 October 2026.

Their business rules differ: the latter describes failed calls as attempts that preserve pipeline status. The local migrated endpoint has its own maintained status policy. Neither remote script was copied over that policy, and neither enabled remote document was changed. The duplicate registration must be resolved before selecting one as the authoritative lead-save implementation.

The enabled `life_cc_mobile_v18` script was read in full. Its desktop `live` branch selects the latest mobile call for the current agent (or a manager-selected agent), returns only the last four phone digits, and exposes whether the call is live. Its other actions include mobile queue, dial, finish, recording and team management; these were not ported as part of the desktop popup.

## Validation

- CC legacy status and dashboard group tests pass.
- Legacy snapshot JavaScript passes `node --check`.
- Vue production build passes, with existing bundle-size and mixed-import warnings.
- Live call behavior and authenticated browser interaction have not been exercised.

Changes are local workspace changes. No ERP Web Page or Server Script was written through the connector.
