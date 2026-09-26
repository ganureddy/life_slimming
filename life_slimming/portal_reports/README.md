# Portal report definitions

`referral_report_fixed.json` is the original `REFERRAL REPORT – FIXED`
Query Report exported through ERP Portal (source modified 2026-09-04).
It includes the SQL, date filters, saved report metadata, and five role entries.
It contains no invoice results or customer records.

Install explicitly on the target site as Administrator:

```sh
bench --site mysite.local execute life_slimming.portal_reports.install.referral_report
```

The installer preserves the source definition, regenerates child-row IDs,
and refuses to overwrite an existing report with different SQL.
Required tables and custom columns must already exist on the target site.

Verified locally with September 1–21, 2026 filters: 24 invoice-level columns,
zero matching local rows. Production transaction data was not imported.
The exported SQL does not apply the supplied branch filter; the existing
Employee Sale Master page separately filters returned rows by branch.
The import does not add or change backend branch authorization.
