# Documents application security verification

Historical foundation checklist. The later portal extension implements the previously absent workflows; current evidence and coverage are recorded in `PORTAL_IMPLEMENTATION.md`, `tests/test_portal.py` and the portal test/HTTP output files. Do not interpret the historical N/A rows as the current implementation status.

Target: `C:\Users\Angel\OneDrive\Documents\CampusOpportunityPlanner`. Date: **3 November 2026**. Live app: **http://127.0.0.1:5000**. Results apply to this copy, not the Desktop\DBMS suite.

| Test | Result |
|---|---|
| CU registration, normalization, matching UID/email and password confirmation | PASS |
| Non-CU/mismatched/malformed identity and weak-password rejection | PASS |
| Secure hash and duplicate identity; public role/is_active mass assignment | PASS |
| UID before/after profile setup, university email, wrong password and inactive account | PASS |
| SQL injection string in login; no authentication bypass | PASS |
| Logged-out profile and diagnostic protection | PASS |
| Student denied diagnostic, admin permitted diagnostic and denied student-only setup | PASS |
| Current role/deactivation rechecked from DB | PASS |
| Profile ownership not reassigned by forged user_id/role | PASS |
| Department exists; valid year/finite CGPA/graduation values | PASS |
| Invalid numeric text, NaN/Infinity, out-of-range year/CGPA and unknown department | PASS |
| Concurrent registration/profile requests produce one account/profile | PASS |
| Every POST form contains CSRF token; missing/Unicode/oversized invalid tokens rejected | PASS |
| Unsafe methods checked; GET logout rejected | PASS |
| Login state rotation; no cookie password/name/authoritative role | PASS |
| Copied-cookie replay after logout rejected | PASS |
| Stored script-like name not executed; reflected payload/flash text escaped | PASS |
| No unsafe template/JS sinks; inline style widths moved to CSS | PASS |
| Safe 400/403/404/405/413/500/503 behavior, sanitized error logs | PASS |
| Production root/missing-host/weak-secret rejection | PASS |
| Production HTTPS/Secure/HttpOnly/SameSite cookie and HSTS | PASS |
| Local HTTP usable; trusted-host rejection and security headers | PASS |
| Login/registration rate limits, Retry-After, X-Forwarded-For spoof resistance | PASS |
| Non-root runtime with narrow grants, no DDL/history write | PASS |
| Additive session/rate tables and immutable-history triggers | PASS |
| Repeated migration retains data and already-correct runtime settings | PASS |
| Configured-secret scan and private-file ACL restriction | PASS |
| pip-audit known advisories / skipped packages | PASS — 0 / 0 |
| pip check | PASS — no broken requirements |
| Eight live HTTP smoke checks on selected Documents server | PASS |
| Upload/download security | N/A — not implemented |
| Search/discovery, apply/withdraw/deadlines/readiness/status workflow tests | N/A — routes not implemented |
| Other-user application/document/task/notification resource-ID tests | N/A — routes not implemented |
| Admin CRUD, status change and associated notification/history workflow | N/A — routes not implemented |
| Git-history secret scan | NOT ASSESSED — no project Git metadata |
| Real production TLS/proxy/infrastructure and visual/mobile review | NOT PERFORMED |

Final automated run: **16 tests passed, zero skips**, with `RUN_MYSQL_TESTS=1`, using actual local MySQL and unique test identities. Only test accounts are deactivated; all rows are retained. Sanitized outputs are under `security-audit/`. Commands and remaining risks are in `SECURITY_AUDIT.md`.
