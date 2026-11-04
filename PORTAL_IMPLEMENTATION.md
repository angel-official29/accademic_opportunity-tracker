# Completed student and admin modules

Target: `C:\Users\Angel\OneDrive\Documents\CampusOpportunityPlanner`, served at http://127.0.0.1:5000. Existing records and the original secure foundation are preserved.

Implemented:

- Role-specific login redirects and dashboards with real database counts.
- Published opportunity discovery with keyword/category/department/skill/mode/deadline/eligibility filters and deadline/newest/readiness sorting.
- Detail view with conditions, required/preferred skills/documents, eligibility reasons, missing requirements and next action.
- Readiness = academic rules 40 + required skills 30 + mandatory documents 20 + linked task completion 10. Empty requirement components receive full credit; availability separately gates applying. This is rule-based preparation guidance, not trained AI or selection probability.
- Save an opportunity, mark document readiness, add/complete/reopen tasks, and submit a saved or new application. Academic/availability failures block apply; missing skills/documents guide preparation.
- My Applications, submission time, immutable status history and allowed withdrawal. Unique(student_id,opportunity_id) prevents duplicate/repeated application records.
- Admin overview, transactional opportunity creation/editing, publish/close/cancel, academic/department/skill/document requirements.
- Applicant search/filter, profile/readiness review, allowed status transitions, private admin notes and transactional student notifications.
- Schema-only MySQL browser for all 21 tables, with no password/hash/token values or real student rows displayed.

Migrations and grants:

`scripts/setup_portal.py` applies `002_portal.sql` only when needed and grants specific DML rights for current routes. No DDL rights, user/application deletes or history mutation rights are granted. Required profile/application updates and junction-table replacements are now permitted. The earlier production guide's minimal foundation grant list is historical; this script is authoritative for the extended portal.

Status lifecycle: saved/preparing → applied; applied → under_review/shortlisted/rejected; under_review → shortlisted/selected/rejected; shortlisted → selected/rejected. Students may withdraw applied/under_review/shortlisted. Selected/rejected/withdrawn are final. Internal review notes are excluded from student history queries.

Security and tests:

- Current full MySQL run: **19 tests passed, zero skips**, output `security-audit/portal-test-results.txt`.
- Full portal test verifies create/edit, filtering, score calculation, save/readiness/tasks, submission/duplicates, ownership, concurrent review/history, notification, withdrawal and academic/deadline/closed rejection.
- Separate rate-limit regression verifies apply/save and review 429/Retry-After. Existing login/registration/session/CSRF/validation/security tests still pass.
- Live HTTP checks: **33 successful authenticated GETs**—six student pages, six admin pages and 21 schema views—recorded in `security-audit/portal-http-results.json`. This is a page-check count, not 33 complete workflows.
- Login limits remain 30/min/IP and 8/min/account, registration 20/hour/IP. New save/apply is 30/min/student; admin review 60/min/admin. Shared MySQL counters and CSRF checks remain enabled in normal runtime.
- Fictional demonstration listings/accounts are separate from real data. Credentials are private in ignored `.report-demo.env` and never embedded in reports or ER diagrams.

Report completion:

The revised technical report describes implemented modules, current evidence and formatted references. Its ER sheets and the complete vector diagram derive from live MySQL key metadata. `Phase_1_Foundation_Report.docx` preserves the previous report.

Submission identity fields await the student's name, UID, section, department and faculty name. Certificate/declaration/acknowledgement requirements await the teacher's requirements; no approval or signature is fabricated. Browser screenshots are blocked by a saved origin permission for localhost:5000. No headless/CDP workaround or fabricated screenshot is substituted. Enable that permission to capture working-page and live MySQL-schema screenshots before marking the report final.

Remaining product/operational limits: no uploads, independent academic/document verification, SSO/email ownership checks, recovery/MFA, production TLS/proxy/remote DB certificate deployment, or automatic retention purge. Scores use current values rather than an immutable submission snapshot. Demographics or other sensitive data do not drive selection; administrators explicitly review fictional/local applications.
