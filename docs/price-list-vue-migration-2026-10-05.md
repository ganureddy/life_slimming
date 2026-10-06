# Price-List Vue migration — 5 October 2026

The portal's `/life_portal/pricelist` route now renders a native Vue page. The
same component is also available at `/life_portal/native/pricelist`. The exported
ERP page remains in the repository but is no longer the portal destination.

The Vue page covers billable therapy rates, minimum and maximum prices, active
offer prices and filtering; regular and LIFErise packages; search and pagination;
and read-only package details with included therapies, dates, GST and amounts.
All records are read from Frappe APIs. The offer API resolves permitted Pricing
Rule parents and their item mappings in one request.

The local site has 353 billable therapies, 91 active templates and 295 enabled
pricing rules. The new read-only offer endpoint returned 27 mapped active offer
items. Unit tests, production compilation and mocked desktop/mobile browser
checks passed. No price, package or payment records were changed. A deploy is
still required before portal users see this route change.
