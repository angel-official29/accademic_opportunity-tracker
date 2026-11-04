"""Build the current implementation report without inventing identity or screenshots."""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.section import WD_SECTION_START,WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT=Path(__file__).resolve().parent
# Reuse the verified typography/table helpers, without running the old report body.
prefix=(OUT/'build_report.py').read_text(encoding='utf-8').split('# Page 1')[0]
exec(compile(prefix,str(OUT/'build_report.py'),'exec'))
metadata=json.loads((OUT/'schema_metadata.json').read_text())
identity_path=OUT/'submission_details.json'
details=json.loads(identity_path.read_text()) if identity_path.exists() else {}
doc.core_properties.subject='Implemented student and administrator opportunity tracker'


def reference(number,author,title,url):
    par=p(f'[{number}] {author}. (n.d.). ')
    r=par.add_run(title+'. '); r.italic=True
    par.add_run('Retrieved November 3, 2026. ')
    link=OxmlElement('w:hyperlink'); rid=par.part.relate_to(url,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True)
    link.set(qn('r:id'),rid); run=OxmlElement('w:r'); prop=OxmlElement('w:rPr'); color=OxmlElement('w:color'); color.set(qn('w:val'),'126C60'); prop.append(color); run.append(prop)
    txt=OxmlElement('w:t'); txt.text='Online documentation'; run.append(txt); link.append(run); par._p.append(link)


def dictionary(title,names):
    chapter(title)
    for name in names:
        h(name.replace('_',' '))
        fields=[r for r in metadata['columns'] if r['TABLE_NAME']==name]
        pairs=[]
        for r in fields:
            fk=any(f['TABLE_NAME']==name and f['COLUMN_NAME']==r['COLUMN_NAME'] for f in metadata['foreign_keys'])
            mark=' '.join(v for v in [('PK' if r['COLUMN_KEY']=='PRI' else 'UQ' if r['COLUMN_KEY']=='UNI' else ''),'FK' if fk else ''] if v)
            pairs.append(r['COLUMN_NAME']+(' ['+mark+']' if mark else ''))
        p('; '.join(pairs)+'.')
    p('PK identifies a primary key, FK a foreign key, and UQ a separately unique field. Composite keys are shown by marking each participating primary-key column. The schema metadata and ER figures are generated from the live MySQL definition.')


p('DBMS PROJECT REPORT','Subtitle')
p('Chandigarh University Academic Opportunity Tracker','Title')
p('Opportunity Compass','Subtitle')
p('Student and administrator portals with explainable eligibility and readiness')
p('Chandigarh University\nNovember 2026')
h('Submission details')
for label,key in [('Student name','student_name'),('University UID','uid'),('Section','section'),('Department','department'),('Faculty name','faculty_name')]:
    par=p(''); par.add_run(label+'  ').bold=True; par.add_run(details.get(key,'________________________________________'))
h('Project implementation')
p('Python Flask and MySQL 8 with HTML CSS JavaScript, session authentication, student preparation workflows and administrator review. The selected application runs at http://127.0.0.1:5000.')

chapter('Abstract')
p('The Chandigarh University Academic Opportunity Tracker supports the student journey from finding an opportunity to preparing and tracking an application. Students maintain academic and skill profiles, search current listings, inspect eligibility explanations, save opportunities, manage document readiness and preparation tasks, submit applications and follow status history. Administrators publish and update opportunities, inspect applicants and record review decisions.')
p('The system uses Flask for server-side routes, Jinja for escaped templates and MySQL for relational persistence. It reuses the existing normalized schema and adds an Under Review application state through a separate migration. Related opportunity requirements and application status changes are saved transactionally. A unique student-opportunity pair prevents duplicate applications.')
p('Eligibility checks academic profile, allowed department, CGPA, year, listing status and deadline. Readiness is a transparent weighted calculation: 40 percent academic rules, 30 percent required skills, 20 percent mandatory documents and 10 percent preparation tasks. It is not a machine learning model and does not guarantee selection.')
p('The current verification evidence records 19 passing automated test methods and 33 successful authenticated HTTP page checks, including all 21 MySQL schema views. Security measures include CSRF tokens, current role and ownership validation, hashed passwords, revocable sessions, rate limits, parameterized SQL and restricted database grants. Demonstration records are explicitly fictional, and screenshots must use these records rather than personal student data.')
h('Scope and boundaries')
p('This report covers the Documents CampusOpportunityPlanner application. Document preparation is a self-reported checklist; no file uploads or independent document verification are implemented. Academic information and skills are self-reported. Production TLS, external identity verification and backup operations remain deployment responsibilities.')

chapter('Contents')
p('The report follows the implementation from requirements through architecture, student workflows, administrator workflows, algorithms, database design, security, testing, operation and references. The final three ER sheets show identity, opportunity and application relationships with PK, FK and unique markers.')
table(['Chapter','Subject'],[
('1','Problem statement and requirements'),('2','Architecture and code responsibilities'),('3','Student portal implementation'),('4','Administrator portal implementation'),('5','Eligibility readiness and status algorithms'),('6','Relational design and normalization'),('7 to 9','Data dictionary for all 21 tables'),('10','Security controls and integrity'),('11','Testing and verified results'),('12','Operation limitations and conclusion'),('References','Formatted technical references'),('ER sheets','Identity opportunities and applications')],[1.3,5.25])

chapter('Problem statement and requirements')
p('Campus opportunities often have different academic conditions, skills, documents and closing dates. A simple listing page does not tell a student why they qualify or what preparation remains. The project combines discovery, understandable rules, personal preparation and application review in one relational application.')
h('Objectives')
p('The system must connect each action to an authenticated student or administrator, calculate guidance from stored records, preserve application history and prevent duplicate or unauthorized changes. It must also make the next action clear: complete a profile, build a required skill, prepare a document, finish a task, submit or wait for review.')
table(['Requirement','Implemented behavior'],[
('Student dashboard','Database counts recommendations deadlines and recent status updates'),('Search and filters','Keyword category department skill mode deadline eligible-only and sorting'),('Eligibility and readiness','Server-side explanations component scores gaps and next action'),('Save and apply','One application record per student and opportunity; saved records can be submitted'),('Application tracking','Submission date status history withdrawal documents and tasks'),('Admin portal','Role redirect overview opportunity editing applicant filtering and review'),('Database evidence','Authenticated schema browser for 21 tables without exposing row secrets')],[1.8,4.75])
h('Technology')
p('The reviewed runtime uses Flask 3.1.3, MySQL Server 8.0.46, MySQL Connector Python 26.10.0, Werkzeug 3.1.9, python dotenv 1.2.4 and Waitress 3.0.2. Flask provides the web framework and server-rendered application conventions [1]. MySQL provides transactions and integrity constraints [2].')

chapter('Architecture and code responsibilities')
p('A browser submits forms to Flask, which authenticates and authorizes the request before reading or updating MySQL. Templates display escaped results. The browser never supplies authoritative eligibility, readiness, account role, owner ID or application state.')
picture()
p('Figure 1  Web application architecture',style='Caption')
table(['File or module','Responsibility'],[
('app.py','Existing registration login setup logout and role-based landing redirects'),('security.py','CSRF account checks revocable sessions limits headers and safe errors'),('database.py','Prepared values query helpers request connection cleanup and transactions'),('student_portal.py','Dashboard search opportunity save/apply profile preparation and ownership'),('admin_portal.py','Overview opportunity transactions review transitions and schema browser'),('portal_services.py','Batched database enrichment eligibility explanations and readiness calculation')],[2,4.55])
p('The migration script grants only the DML operations required by implemented routes. MySQL metadata is read through INFORMATION_SCHEMA for the schema browser and ER export. No environment values, password hashes or session tokens are rendered in that browser.')

chapter('Student portal implementation')
h('Dashboard and discovery')
p('After login, a student reaches the dashboard. It displays profile completion, active submitted applications, saved opportunities, upcoming deadlines, recommendations and recent application updates. Recommendations are ordered by eligibility and readiness. A student without an academic profile receives a setup action rather than an invented eligibility result.')
p('Discovery lists published opportunities whose deadlines remain open. It supports keyword, category, department, skill, mode, closing-date and eligible-only filters. Sorting uses fixed deadline, newest or readiness choices. Each card shows organization, category, academic requirements, deadline, eligibility, readiness and the student application state.')
h('Opportunity and preparation')
p('The detail page presents the full description, department restrictions, academic limits, required or preferred skills, documents and explainable score. Saving creates a unique application in the saved state without claiming it is submitted. The student can then mark document readiness and add dated tasks. Completing or reopening a task changes the corresponding preparation component.')
p('The profile page updates academic details and self-reported skill levels. Skill matching checks whether a required skill is present; the schema does not define minimum skill proficiency thresholds. Required documents are ready only when their application checklist state is ready, submitted or approved.')
h('Applications and status')
p('An eligible student may submit directly or submit a saved record. The backend locks the opportunity, rechecks its current status and deadline, then records applied status and submission time with history. A repeated submission does not create another record. My Applications combines saved and submitted records and links to detailed history, documents and tasks. Students can withdraw applied, under-review or shortlisted applications; selected, rejected and withdrawn states are final.')
table(['Route group','Student action'],[('/student/dashboard','Personal overview'),('/student/discover','Search and filters'),('/student/opportunities/id','Details save and apply'),('/student/applications','Saved and submitted list'),('/student/applications/id','History checklist tasks and withdrawal'),('/student/profile','Academic and skill updates')],[2.7,3.85])

chapter('Administrator portal implementation')
h('Authentication and overview')
p('Students and administrators use the same secure sign-in form. The backend redirects administrators to their own dashboard using the database role. Student routes reject administrators and admin routes reject students. The overview uses real SQL counts for active students, open opportunities, submitted applications and pending reviews, with category and status distributions.')
h('Opportunity management')
p('Administrators create or edit organization/category assignment, title, description, mode, location, deadline, optional dates, stipend and external information URL. They define year/CGPA limits, allowed departments, required/preferred skills and mandatory documents. Listing states include draft, published, closed and cancelled. Closing or cancelling retains applications.')
p('The main listing and its academic and junction-table requirements save in one transaction. Every foreign selection must exist. Dates, numeric limits, http or https URLs and mutually exclusive required/preferred skills are checked server-side. The opportunity row also provides the serialization boundary against a concurrent application.')
h('Applicant review')
p('The applicant list supports search and status filtering. Review shows the applicant profile, skill evidence, current readiness, document checklist and audit trail. Allowed transitions are submitted to Under Review, Shortlisted or Rejected; Under Review to Shortlisted, Selected or Rejected; and Shortlisted to Selected or Rejected. Saved/preparing and final states cannot receive review decisions.')
p('A review transaction locks the application and atomically updates status, inserts an immutable history record and creates a student notification. Internal notes are visible only to administrators. Current scores may change when profile or opportunity requirements change; they are not immutable submission snapshots.')
h('Database schema browser')
p('The admin-only schema browser shows live column names, types, nullability, primary/unique markers and foreign-key targets for all 21 tables. It is a metadata interface, not a display of passwords, token values or real student records. It supplies a safe view for MySQL structure evidence.')

chapter('Eligibility readiness and status algorithms')
h('Academic and availability rules')
p('The eligibility service checks for a usable academic profile, allowed department when restricted, minimum CGPA when greater than zero, year within the configured bounds, published listing state and a future application deadline. Every rule produces a true/false explanation. An absent condition is not replaced with a guessed value.')
h('Transparent readiness formula')
table(['Component','Weight','Calculation'],[
('Academic eligibility','40','Fraction of applicable academic checks satisfied'),('Required skills','30','Fraction of required skill IDs present in student skills'),('Mandatory documents','20','Fraction of mandatory checklist documents ready'),('Preparation tasks','10','Fraction of linked tasks completed')],[1.9,.8,3.85])
p('Total readiness is the sum of weighted components, rounded to a percentage. A component with no requirements receives full credit. Preferred skills do not reduce the score. Listing availability is a separate eligibility gate: a closed opportunity can still have a high preparation score but cannot accept an application. Missing skills/documents guide preparation; academic eligibility and availability control submission.')
h('Worked example')
p('A student who satisfies all academic rules, has one of two required skills, one of two mandatory documents ready, and one of two tasks complete receives 40 + 15 + 10 + 5 = 70 percent. A student with all required evidence and completed tasks receives 100 percent. The result represents recorded preparation, not a selection probability.')
h('Application lifecycle')
p('Save creates saved and an initial history record. Apply changes saved/preparing to applied or creates applied directly, with applied_at set. Admin review follows the allowed transitions above. Withdrawal is permitted only before a final outcome. Unique(student_id, opportunity_id) prevents duplicate records even after withdrawal. Each history entry records actor, old/new status and time.')

chapter('Relational design and normalization')
p('The live database contains 19 original domain tables and two security tables. Identity, academics, reference data, requirements and operational records are separated. Junction tables represent repeated relationships without comma-separated lists. Foreign keys connect existing parents and children; unique keys constrain identity and duplicate relationships [2].')
table(['Relationship','Cardinality'],[
('users to student_profiles','One to zero or one; user_id unique in profile'),('departments to student_profiles','One to zero or many'),('student_profiles to skills','Many to many through student_skills'),('organizations or categories to opportunities','One to zero or many'),('opportunities to eligibility_requirements','One to zero or one'),('students to opportunities','Many to many through applications'),('applications to status history tasks documents','One to zero or many'),('users to auth_sessions','One to zero or many')],[4.1,2.45])
h('Normalization')
p('Atomic columns and separate relationship rows support first normal form. In composite-key junctions, proficiency, requirement type and document state describe the complete pair, supporting second normal form. Department, organization, category, skill and document descriptions are stored once in reference tables rather than copied into applications. This limits transitive duplication and follows the intent of third normal form.')
h('Migrations and integrity')
p('The first security migration adds sessions, rate buckets and rejecting history update/delete triggers. The portal migration adds under_review at the end of the application enum, preserving existing labels. No table is dropped and no existing record is reset. Foreign-key cascades remain; a privileged parent deletion can bypass child history triggers, so future deletion policies need separate retention review. The runtime has no user/application delete permission.')

dictionary('Student and identity data dictionary',['users','student_profiles','departments','skills','student_skills','student_interests'])
dictionary('Opportunity and application data dictionary',['organizations','opportunity_categories','opportunities','eligibility_requirements','opportunity_departments','opportunity_skills','applications','application_status_history'])
dictionary('Document preparation and security dictionary',['document_types','opportunity_documents','application_documents','preparation_tasks','notifications','auth_sessions','security_rate_limits'])

chapter('Security controls and integrity')
table(['Control','Implemented behavior'],[
('Authentication','CU UID/email consistency, password length and Werkzeug hashing with generic login errors [3]'),('Sessions','Opaque token with server-side digest and absolute expiry; logout revocation and current account check'),('Authorization','Reusable roles plus student-scoped application/document/task/profile queries'),('CSRF','Every POST form has a random session token; invalid/missing tokens rejected before action'),('SQL and transactions','Parameterized request values, allowlisted identifiers, rollback and cursor/connection cleanup'),('Rate limits','Login IP/account, registration IP, student apply/save and admin review with MySQL atomic counters'),('Browser and errors','CSP, frame denial, no-sniff, referrer and permissions policy, safe errors and no-store'),('Database grants','Dedicated non-root runtime, no DDL, no history mutation and narrowly scoped table rights')],[1.5,5.05])
p('Login allows 30 attempts/minute per direct IP and 8 per normalized account; registration allows 20/hour per direct IP. Save/apply allows 30/minute per student and review 60/minute per admin. Limits are shared across workers, return Retry-After and ignore untrusted forwarding headers.')
p('No file upload is claimed. Document readiness and skills are self-reported. Local private files are ignored and access-restricted, but production must move migration credentials outside the runtime-readable identity. The audit identified no configured-secret exposure in scanned project text. A passing scan or test does not establish that every infrastructure or unknown vulnerability is absent.')

chapter('Testing and verified results')
p('The current full run passed 19 automated test methods with MySQL tests enabled and zero skips. The suite includes the original 16 security tests, a complete portal workflow test, a readiness rule test and a portal mutation rate-limit test. Nested assertions exercise multiple conditions within each method. The standard unittest framework organizes the automated checks [5].')
table(['Verification','Evidence','Result'],[
('Student and admin login redirects','Role-specific dashboard and cross-role 403','Pass'),('Opportunity management','Create/edit listing and all related requirements','Pass'),('Discovery','Keyword category department skill mode eligible and score sort','Pass'),('Readiness','Exact weights, gaps, documents/tasks and 100-percent completion','Pass'),('Save and apply','Saved-to-applied transition and duplicate prevention','Pass'),('Ownership','Another student denied application document task and withdrawal actions','Pass'),('Review and history','Concurrent requests produce one transition; private notes withheld','Pass'),('Notifications and withdrawal','Atomic student notification and terminal-state rules','Pass'),('Security regression','CSRF injection escaping sessions input errors and grants','Pass'),('Abuse control','Apply and review limits return 429/Retry-After','Pass')],[1.65,4.2,.7])
p('A separate live HTTP run made 33 successful authenticated GET checks: six student pages, six admin pages and 21 MySQL schema views. These are page checks, not 33 distinct user workflows. JSON records retain path, role and status without cookies or passwords.')
p('The recorded pip-audit package scan found zero known advisories and zero skipped packages; pip check found no broken requirements [4]. The current source and live schema are the evidence for CSRF, rate limiting and restricted access claims. Raw sanitized outputs remain with the project for review.')

chapter('Operation limitations and conclusion')
h('Run and verify')
p('Use the Documents CampusOpportunityPlanner directory and launch start.ps1. The local URL is http://127.0.0.1:5000. Apply scripts/setup_portal.py with private migration credentials when moving an existing audited database to the portal version. The schema name remains campus_opportunity_planner.')
p('.\\.venv\\Scripts\\waitress-serve.exe --listen=127.0.0.1:5000 app:app')
p('Tests: set RUN_MYSQL_TESTS=1 and run python -m unittest discover -s tests -v. Run scripts/portal_live_checks.py for current live page evidence. Use generated fixtures only; do not run fixture tests on a production dataset.')
h('Demonstration data')
p('Eight opportunities, fictional organizations and dedicated demonstration identities support review. Their descriptions explicitly state they are not real openings. Report screenshots should use these accounts. Demonstration passwords stay only in ignored local environment configuration and are not included in this report.')
h('Remaining limitations')
p('No upload pipeline, email ownership verification, university SSO, password recovery or MFA is implemented. Academic values and skills are self-reported. No external decision should treat readiness as verified academic evidence or an automated selection probability. Production TLS, proxy trust, remote-database TLS, backups, retention and independent audit storage require deployment review.')
p('The original landing-page readiness card is labelled as illustrative. Student and admin dashboards use real database queries. Current readiness recalculates from current data and is not a stored historical submission snapshot.')
h('Conclusion')
p('The implemented system now supports the main student and administrator opportunity-tracking cycle rather than only account setup. Students discover, evaluate, save, prepare, apply and track; administrators manage requirements and review applicants. A normalized MySQL schema, explicit rules and testable transaction/authorization controls provide the basis for further production work.')

chapter('References')
reference(1,'Pallets Projects','Flask documentation Version 3.1','https://flask.palletsprojects.com/en/stable/')
reference(2,'Oracle','MySQL 8.0 Reference Manual','https://dev.mysql.com/doc/refman/8.0/en/')
reference(3,'Pallets Projects','Werkzeug utilities and security helpers','https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security')
reference(4,'Python Packaging Authority','pip audit project documentation','https://github.com/pypa/pip-audit')
reference(5,'Python Software Foundation','unittest Unit testing framework','https://docs.python.org/3/library/unittest.html')
h('Project evidence')
p('Implementation: app.py, student_portal.py, admin_portal.py, portal_services.py, database.py and security.py. Schema: database/schema.sql and separate migrations. Verification: tests/test_security.py, tests/test_portal.py, security-audit/portal-test-results.txt and security-audit/portal-http-results.json. ER export: reports/schema_metadata.json contains schema metadata only, not personal record values.')

for title,filename in [('ER diagram for student identity','er_students.png'),('ER diagram for opportunity requirements','er_opportunities.png'),('ER diagram for applications and review','er_applications.png')]:
    s=doc.add_section(WD_SECTION_START.NEW_PAGE); s.orientation=WD_ORIENT.LANDSCAPE
    s.page_width=Inches(16.54); s.page_height=Inches(11.69); s.left_margin=s.right_margin=Inches(.65); s.top_margin=s.bottom_margin=Inches(.6)
    doc.add_heading(title,1)
    from PIL import Image
    image=Image.open(OUT/filename); w,hpx=image.size
    width=min(15.15,8.5*w/hpx)
    doc.add_picture(str(OUT/filename),width=Inches(width))
    p('Live MySQL metadata defines the PK FK UQ markers and directed parent-to-child relationships. A separate er_complete.svg preserves all 21 table structures for zoomed inspection. Schema table screenshots are a distinct evidence item.')

for root in (doc.element,doc.styles.element):
    for border in root.xpath('.//w:pBdr'): border.getparent().remove(border)
output=OUT/'Academic_Opportunity_Tracker_Completed_Modules_Review.docx'
doc.save(output)
print(output)
