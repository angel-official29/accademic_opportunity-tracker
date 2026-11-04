**Historical foundation audit.** Student and administrator workflows were subsequently implemented in this same Documents project. The current suite has 19 passing methods and 33 successful authenticated page checks. See `PORTAL_IMPLEMENTATION.md`; the original findings/results below are retained as audit history.

| ID | Severity | Category | Location | Evidence | Impact | Fix |
|---|---|---|---|---|---|---|
| D01 | High | Debugger | `app.py`, original main block; patched line 135 | Original `app.run(debug=True)` enabled Werkzeug debugger/reloader | Malformed authenticated profile input could expose tracebacks/debugger. Code execution would additionally require access to an unlocked console; no such exploitation was attempted | **Fixed:** explicit debug/debugger/reloader false; live server replaced with Waitress |
| D02 | High | Database privileges | `database.py:get_db_connection`; live pre-patch grants | Flask used MySQL root with elevated global privileges | A compromised SQL/runtime connection could affect databases beyond this application; no SQL-injection vulnerability was found | **Fixed for runtime:** generated dedicated `cu_documents` account with minimal table-specific grants; original privileged credentials separated into ignored `.migration.env`, original root account unchanged |
| D03 | Medium | CSRF / HTTP semantics | Registration/login/profile templates; `app.py:logout` | No CSRF token checks; logout accepted GET | Login/profile/registration requests had no token defense; a cross-site top-level GET could force logout | **Fixed:** tokens on every POST form, unsafe-method checks, optional header token, POST-only logout button |
| D04 | Medium | Session revocation / authorization | Original `profile_setup`, login/logout | Cookie role was authoritative; active account/role not re-read; logout only cleared cookie | An account disabled or reassigned after login retained session authority; a copied cookie could be replayed after logout | **Fixed:** live account/role query, reusable role guard, server-side hashed session records and per-session revocation |
| D05 | Medium | Identity / password validation | `app.py:register/profile_setup` | Original registration accepted arbitrary email and any nonempty matching password; UID was independent of email | Weak accounts and inconsistent/non-CU identities could be created | **Fixed:** matching lowercase CU UID/email and backend 10–128 character password rule for new registrations; existing accounts not rewritten |
| D06 | Medium | Brute force / abuse | `app.py:login/register` | No attempt counters or rate limiter | Repeated guesses and scrypt/database resource abuse were unrestricted | **Fixed:** process-independent MySQL counters, direct-IP/account limits, 429/Retry-After |
| D07 | Medium | Input validation / safe cleanup | Original `profile_setup`; database operations | Unhandled float/int conversion; ranges/foreign IDs delegated to DB; no finally cleanup on errors | Invalid numeric/foreign-key input caused errors, and debug mode could disclose details; failed operations lacked reliable cleanup | **Fixed:** explicit finite/range/identity/foreign-key checks; request-scoped cursor closure, rollback and connection teardown; safe generic errors |
| D08 | Low | Information disclosure | `app.py:database_test` | Public diagnostic used SHOW TABLES and returned table count | Anonymous users could probe database availability/schema size | **Fixed:** same URL now requires active admin and returns generic availability only |
| D09 | Low | Deployment / headers | Original Flask config and `templates/index.html` | No production guardrails/security headers; three static inline progress widths | Insecure deployment choices and missing browser hardening | **Fixed:** strong-key validation, production root/trusted-host/HTTPS checks, secure cookies, compatible CSP and other headers; widths moved to CSS |

Audit date: **3 November 2026**, Asia/Kolkata. Target: **`C:\Users\Angel\OneDrive\Documents\CampusOpportunityPlanner`**, explicitly selected by the user. These findings concern this original Documents project, not the separate Desktop\DBMS project audited earlier. No confirmed Critical finding was identified. High/Medium findings above were patched; remaining boundaries are documented below. This is not a claim of complete security.

## Initial architecture and inspection

The original app had six endpoints: `/`, `/register`, `/login`, `/profile/setup`, `/logout`, `/database-test`. It used one Flask app, direct MySQL connections, environment-based secrets, Werkzeug hashes and signed Flask cookies. Student profile queries used the cookie user ID, not a form-provided owner. Email, UID, profile/user and student/opportunity uniqueness existed in MySQL. Values in SQL were parameterized. Jinja escaped rendered text. These existing protections were retained.

The actual Python files, templates, CSS/JavaScript, schema/seed, gitignore, installed package metadata and live MySQL constraints/grants were inspected before changes. No `.git` metadata/history was present. Private `.env` values were read only for local connection and comparison; no password, password hash, signing key or authenticated cookie was printed. No configured secret was found in scanned source, SQL, templates, documentation or project logs.

The supplied schema has opportunity/application/document/task tables, but **no corresponding application routes**. The audit did not invent tests or claim protection for absent workflows. The static readiness card and `#` navigation placeholders remain pre-existing product limitations. This audit preserved the original application rather than replacing it with the more complete DBMS copy.

## Scope results

| Requested area | Result |
|---|---|
| Secret management | `.env` ignored; placeholder-only development/production examples added; root settings moved to ignored `.migration.env`, runtime generated separately. Both private files now have owner/SYSTEM-only Windows ACLs. Exact configured-secret scan passed. Git history, prior cloud/screenshot/backups were unavailable/outside this local scan. No confirmed source/log exposure requiring automatic secret rotation was found. |
| Authentication | CU registration identity/password validation, lowercase values, matching UID/email, hashes, duplicate identities, UID/email login, wrong-password/inactive handling and no public admin mass assignment tested. Before profile completion, UID can resolve the matching CU email. Legacy email POST field stays compatible. Admin email login works. CLI admin creation prompts securely and stores a hash. |
| Authorization / IDOR | Profile setup requires an active student from the database; diagnostic requires active admin. Role change/deactivation affects the next request. Forged user/role form values cannot assign another user's profile. No resource-ID endpoints for applications/documents/tasks/notifications exist here; IDOR on those absent routes is not testable. |
| SQL injection | Existing and patched user values use connector parameters. Login injection payload fails normally. No search/sort routes exist. Migration GRANT identifiers come from a fixed server-side mapping; these are not user-controlled f-strings. |
| CSRF | Every POST form has a token. Registration/login/profile/logout reject missing/invalid/non-ASCII/oversized tokens safely. PUT/PATCH/DELETE are checked too. No AJAX writes exist; header token support is available for future code. GET logout now returns 405 with Allow preserved. |
| Sessions | Cookie has user ID/opaque token/CSRF/lifetime/flash metadata, not password/hash/name/profile/authoritative role. Login clears/rotates session state. Server records contain token digests and absolute eight-hour expiry. Copied-cookie replay after logout fails. Legacy pre-patch cookies require signing in again. |
| Input validation | New UID uses ASCII CU pattern and matching email; name/password limits enforced. Profile checks department existence, year 1–4, optional finite CGPA 0–10 and optional graduation current year through +10. NaN/Infinity/bad text/unknown IDs/mismatched identity fail safely. Protected fields are ignored. |
| XSS/templates | No unsafe Jinja `safe` filter or untrusted innerHTML sink found. User-controlled flash text is escaped; stored script-like names are not executed/rendered as markup. No application URL input/JSON embedding/URL-fetch feature exists. Static inline widths were replaced with equivalent CSS classes so CSP needs no unsafe-inline. |
| Uploads | **Not applicable:** no upload/download route or file storage exists. File-name columns alone are not an upload implementation. |
| Admin | Admin is never created by public registration. Interactive creation hashes passwords. The only implemented admin-only endpoint is a generic DB health check. No admin CRUD/status-review routes exist; they were not claimed as tested. |
| Business logic | Profile ownership uses the authenticated user; concurrent profile insertion is constrained by UNIQUE(user_id/UID), and duplicate-account insertions by UNIQUE(email). No apply/withdraw/readiness engine exists in this copy; deadline/status/readiness abuse testing is **not applicable yet**. |
| Errors | Debugger/reloader off. Safe HTTP errors and database 503/unexpected 500 handling tested, including sanitized logs. Errors log event/class/endpoint rather than exception messages, SQL, request data or secrets. Connections/cursors close and transactions roll back. |
| Headers | CSP, no-sniff, frame denial, same-origin referrer, Permissions-Policy and no-store tested on routes/errors and live HTTP. Trusted hosts enforced. HSTS only on production HTTPS. Local HTTP cookies intentionally omit Secure; production forces it. |
| Dependencies | All installed packages checked by PyPA pip-audit 2.10.1: **zero known advisories, zero skipped packages**. Includes MySQL Connector/Python **26.10.0**, preserving this project's installed version rather than downgrading to the other project's connector. `pip check` passed. Exact pins added. Audit tool remained in the separate earlier audit environment, not runtime dependencies. |
| Database | Live MySQL **8.0.46** PK/FK/UNIQUE/CHECK constraints inspected. Original schema/data/cascades retained. Additive session/limiter tables and immutable-history DML triggers added. Runtime has no DDL, account update/delete, or history mutation rights. Root password/grants were not altered. |
| Rate limiting | Login: 30/minute direct IP and 8/minute normalized account; registration: 20/hour direct IP. HMAC bucket identifiers, atomic row locks, counters shared by workers. Safe tests observe Retry-After/429 and confirm changing X-Forwarded-For does not bypass the direct-IP bucket. Apply/admin status routes do not exist and therefore have no endpoint limiter to test. |
| Races / duplicates | Concurrent same-identity registration yields one user; concurrent profile setup yields one profile. UNIQUE constraints arbitrate conflicts; IntegrityError is handled and rolled back. Requests retain safe success/validation responses without requiring excessive runtime lock permissions. No destructive load test was performed. |

## Code/data changes

Existing route names and template appearance remain. The necessary behavioral changes are POST logout, student CU registration validation/UID login, server-side session/account checks, and restricting `/database-test`. Existing account passwords/emails and completed profiles were not silently changed. Legacy non-CU accounts may still log in by their existing email; a legacy uncompleted account needs trusted identity correction before new CU-only profile rules can be satisfied.

`database/migrations/001_security.sql` adds `auth_sessions`, `security_rate_limits`, and two history update/delete triggers. MySQL 8.0.29+ is required for idempotent CREATE TRIGGER syntax. `scripts/harden_database.py` provisions only the dedicated local runtime account and preserves original root settings in the private migration file. It was rerun successfully after correcting a Windows/OneDrive replacement issue; already-correct runtime settings are left untouched on repeats. DDL/grants commit implicitly, so back up before production migration.

No existing table or record was deleted, dropped or reset. Tests insert uniquely generated fixture accounts/profile/session/counter rows and deactivate **only those fixture accounts** afterward; rows are retained for auditability. No real account was deactivated or profile reassigned. The original debug processes were stopped after verifying their project identity. An earlier DBMS worker occupying 5000 was also stopped by verified command line; DBMS remains separate on 5001. The selected Documents copy is now served by Waitress at **http://127.0.0.1:5000**.

## Verification

- **16 automated tests passed**, with MySQL tests explicitly enabled and no skips. Seven anonymous/HTTP/configuration tests and nine database-security tests include nested assertions.
- **Eight live HTTP smoke checks passed** against the Documents server on port 5000: home/security headers, login page, registration page, logged-out profile protection, missing-CSRF rejection, UID login/profile, diagnostic role restriction, and POST logout/protected access.
- Exact configured-secret scan, non-root/table-level grants, READ COMMITTED session isolation, history trigger presence, template sink/token scan and safe error logging passed.
- Installed-package advisory scan: zero known vulnerabilities, no skipped packages; dependency compatibility check passed.
- The first runtime test found a locking statement requiring a privilege beyond the chosen minimal grant. It was removed in favor of UNIQUE-constrained insertion with safe conflict handling. An added test method initially had a misplaced block; that test error was corrected before the final passing run. No permission broadening was used to hide the failures.
- Browser/mobile visual review, real production TLS/proxy deployment, external systems and destructive attacks were not performed.

Sanitized output: `security-audit/test-results.txt`, `security-audit/live-smoke-results.txt`, `security-audit/config-verification.txt`. Package audit JSON remains local and ignored.

## Exact verification commands

Executed in PowerShell from the Documents project. No real credential was passed on a command line.

```powershell
.\.venv\Scripts\python.exe scripts\harden_database.py
.\.venv\Scripts\python.exe -m pip install waitress==3.0.2
.\scripts\protect_private_files.ps1
$env:RUN_MYSQL_TESTS='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath security-audit\test-results.txt
& 'C:\Users\Angel\OneDrive\Desktop\DBMS\.audit-venv\Scripts\python.exe' -m pip_audit --path .venv\Lib\site-packages --format json --output security-audit\dependency-audit.json
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\verify_security.py 2>&1 | Tee-Object -FilePath security-audit\config-verification.txt
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:5000 app:app
.\.venv\Scripts\python.exe scripts\security_live_smoke.py 2>&1 | Tee-Object -FilePath security-audit\live-smoke-results.txt
```

The server was launched hidden with Start-Process and ignored log files. The quoted audit executable is the existing official PyPA tool from the earlier separate environment. It did not add audit dependencies to this application's environment.

## Remaining risks and limitations

1. **Privileged migration credentials / OneDrive:** `.migration.env` is retained locally to preserve the user's original root configuration and allow migration. ACLs restrict it, but the same OS user running Flask can still read it. Production must put migration credentials outside the runtime-readable directory under a separate identity/secret store. Existing OneDrive copies/backups cannot be revoked by local ACL changes. No confirmed leak was found; rotate if these private files have been shared.
2. **Unimplemented workflows:** opportunity discovery, eligibility/readiness calculations, application submission/history management, tasks, document workflows and admin CRUD do not exist in this copy. Their security cannot be certified from schema alone. Implementing them requires new authorization, validation, CSRF and business-logic tests.
3. **Identity trust:** CU email validation checks format/consistency, not ownership. No university SSO/email verification, MFA or password recovery exists. Academic information is self-reported. Do not equate it to verified university records.
4. **History boundary/cascades:** DML triggers prevent direct history UPDATE/DELETE, and runtime has neither. Existing FK cascades are preserved; privileged parent deletion can remove history without firing child triggers. No such route or runtime delete privilege exists here. A future deletion workflow needs an explicit retention design. A fully privileged DBA can also alter schema/grants/triggers.
5. **Production operations:** real TLS/proxy boundaries, remote DB certificate verification if used, host/account security, patching, monitoring and backup/restore need a deployment review. Local passing tests do not prove production infrastructure security.
6. **Availability/retention:** fixed-window limits need tuning for campus/shared addresses and distributed attacks. Counter/session/fixture rows are not purged under this audit's no-deletion rule; establish a reviewed retention policy.
7. **Coverage:** no Git history was available. External copies, system/cloud logs and historical screenshots/backups were not exhaustively inspected. Known-advisory absence is not proof of package/OS/MySQL/application safety.

See `SECURITY_PRODUCTION.md` for the production configuration. Primary guidance: [Flask security](https://flask.palletsprojects.com/en/stable/web-security/), [Flask configuration](https://flask.palletsprojects.com/en/stable/config/), [PyPA pip-audit](https://github.com/pypa/pip-audit), [MySQL triggers](https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html).
