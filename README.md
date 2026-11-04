# Opportunity Compass — Documents project

This is the original local Flask + MySQL application in **`C:\Users\Angel\OneDrive\Documents\CampusOpportunityPlanner`**, hardened by the defensive audit. It is separate from the larger Desktop\DBMS copy. The Documents application runs at **http://127.0.0.1:5000**.

The Documents application now includes separate student/admin dashboards, opportunity search and filters, explainable eligibility/readiness, save/apply, My Applications, status history/withdrawal, document-readiness checklists, preparation tasks, profile/skills editing, opportunity management and applicant review. The MySQL schema browser shows metadata without secret record values. The original account/security code and existing data were preserved. The public landing-page readiness card is labelled as an illustrative example; authenticated dashboards use real queries.

## Run

The local `.env` is already configured, the security migration applied, and a restricted runtime account provisioned. Existing database name/data and the MySQL root account are retained. The server was verified through Waitress, without a debug reloader.

The portal migration `database/migrations/002_portal.sql` adds `under_review` to the application states. Apply it and the portal-specific runtime grants with `python scripts/setup_portal.py` after the security migration. `python scripts/seed_portal_demo.py` creates eight explicitly fictional opportunities and dedicated demonstration accounts once. Their generated credentials remain private in ignored `.report-demo.env`; never copy that file into the report or source control.

```powershell
Set-Location C:\Users\Angel\OneDrive\Documents\CampusOpportunityPlanner
.\start.ps1
```

If the server is already running on port 5000, use it instead of starting another listener. Stop a foreground server with Ctrl+C. Direct `python app.py` also binds localhost:5000, with debugger and reloader explicitly disabled; Waitress is preferred.

For another environment, create a virtual environment, install `requirements.txt`, configure `.env` from the placeholder-only example with a random private Flask key and database credentials, and review/apply `database/migrations/001_security.sql` using separate migration credentials. Never use the Flask runtime account for schema administration. See `SECURITY_PRODUCTION.md`.

## Authentication and compatibility

- New student registrations require a CU UID and matching `UID@cuchd.in` email. Both are normalized to lowercase. UID uses two ASCII intake digits, 2–5 program letters and 4–6 numeric digits. Passwords require 10–128 characters; only Werkzeug hashes are inserted.
- Students can log in by UID or email. Before academic profile completion, UID lookup falls back to the matching CU email. The old `email` POST field remains accepted for compatibility. Administrators use email.
- Pre-existing non-CU email accounts were not renamed/deleted and can still log in by their existing email. A legacy account without a profile needs its identity corrected through a trusted administrative process before the new CU-only profile validation can be satisfied. No email-ownership verification or CU SSO is implemented.
- Existing completed profiles keep their original setup-completed redirect. Setup is not an edit screen. New profiles validate department existence, year 1–4, optional CGPA 0–10 and optional graduation year from this year through ten years ahead. User/role fields in form data never change ownership or privileges.
- Old cookies require a fresh login after the security migration. New sessions use revocable server-side records, with only identifiers/tokens in the signed cookie, and expire after eight hours. Logout is now a CSRF-protected POST button.
- `/database-test` keeps its URL but requires an active administrator and returns generic availability. The admin portal is `/admin/dashboard`; students use `/student/dashboard`. Role redirects occur after login. Create an administrator with `.\.venv\Scripts\python.exe scripts\create_admin.py` using prompted passwords.

## Security files and tests

`.env` contains runtime credentials and the existing Flask secret. `.migration.env` retains the original privileged connection settings solely for local schema operations. Both are ignored and Windows ACL-restricted. Root's password/grants were not changed; Flask no longer uses root. In production, move migration credentials outside the web process's readable files and keep them under a separate operations identity.

```powershell
$env:RUN_MYSQL_TESTS='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\verify_security.py
.\.venv\Scripts\python.exe scripts\security_live_smoke.py
.\.venv\Scripts\python.exe scripts\portal_live_checks.py
.\.venv\Scripts\python.exe -m pip check
```

MySQL integration tests create unique audit fixtures and deactivate only those accounts afterward. They do not delete existing records. Run against this reviewed local database or a separately migrated test database, never a production dataset. The live smoke script targets localhost:5000 only and uses its own generated fixture account.

See [SECURITY_AUDIT.md](SECURITY_AUDIT.md), [SECURITY_TEST_CHECKLIST.md](SECURITY_TEST_CHECKLIST.md) and [SECURITY_PRODUCTION.md](SECURITY_PRODUCTION.md).

Current portal evidence is in `security-audit/portal-test-results.txt` (**19 passing test methods**) and `security-audit/portal-http-results.json` (**33 successful authenticated GET checks**, including 21 schema views). Tests use real MySQL and generated fixture identities. The original security documents retain their historical foundation-audit results; see `PORTAL_IMPLEMENTATION.md` for the current extension and report completion status.
