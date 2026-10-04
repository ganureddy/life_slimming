# Data Correction

The ERP Web Page `data-correction` (modified 2026-09-20) is available at
`/life_portal/data-correction` and under Main → Data Correction. The shared
module bridge maps `life_data_correction_api` to the existing authenticated
Python endpoint. Its source hash was verified against ERP on 2026-10-04.

`doctypes.json` contains the four ERP schema definitions, with export metadata
removed and the module assigned to this app. The after-migrate setup creates
missing custom DocTypes and adds missing fields without replacing existing
fields, permissions, correction rules or business records. Child tables are
installed before the request schema. Run the normal site migration when
deploying, or execute `life_slimming.api.data_correction_setup.execute`.

The connected ERP account denied read access to correction-rule records, so
rules are not bundled. The development site already has 39 rules. A fresh site
needs its own approved rule configuration and the source DocTypes/fields that
those rules reference. Existing API role and branch checks remain unchanged.
No correction requests were created, approved or posted during validation.
