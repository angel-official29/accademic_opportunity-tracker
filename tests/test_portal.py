"""End-to-end MySQL checks for the completed student and admin modules."""
import os
import secrets
import unittest
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from werkzeug.security import generate_password_hash
from app import app
from portal_services import assess
from test_security import privileged


class ReadinessTest(unittest.TestCase):
    def test_explainable_weights_and_availability(self):
        now=datetime.now(); profile=dict(department_id=1,current_year=3,cgpa=8)
        o=dict(minimum_cgpa=7,minimum_year=2,maximum_year=4,all_departments_allowed=False,listing_status='published',application_deadline=now+timedelta(days=1))
        skills=[dict(skill_id=1,skill_name='Python',requirement_type='required')]
        docs=[dict(document_type_id=1,document_name='Resume',is_mandatory=True)]
        r=assess(profile,o,[1],skills,docs,set(),set(),[dict(task_status='pending')],now)
        self.assertTrue(r['eligible']); self.assertEqual(r['score'],40)
        r=assess(profile,o,[1],skills,docs,{1},{1},[dict(task_status='completed')],now)
        self.assertEqual(r['score'],100)
        self.assertFalse(assess(profile,{**o,'listing_status':'closed'},[1],skills,docs,{1},{1},[],now)['eligible'])
        self.assertFalse(assess({**profile,'department_id':2},o,[1],[],[],set(),set(),[],now)['eligible'])
        self.assertFalse(assess({**profile,'cgpa':6},o,[1],[],[],set(),set(),[],now)['eligible'])
        self.assertFalse(assess({**profile,'current_year':1},o,[1],[],[],set(),set(),[],now)['eligible'])


@unittest.skipUnless(os.getenv('RUN_MYSQL_TESTS')=='1','Requires local MySQL portal migration')
class PortalFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True,RATE_LIMIT_ENABLED=False)
        cls.password=secrets.token_urlsafe(20); cls.suffix=secrets.token_hex(5); cls.ids=[]; cls.opportunities=[]
        with privileged() as c:
            c.execute('SELECT department_id FROM departments LIMIT 1'); cls.dep=c.fetchone()['department_id']
            c.execute('SELECT organization_id FROM organizations LIMIT 1'); cls.org=c.fetchone()['organization_id']
            c.execute('SELECT category_id FROM opportunity_categories LIMIT 1'); cls.cat=c.fetchone()['category_id']
            c.execute('SELECT skill_id FROM skills LIMIT 1'); cls.skill=c.fetchone()['skill_id']
            c.execute('SELECT document_type_id FROM document_types LIMIT 1'); cls.doc=c.fetchone()['document_type_id']
            cls.emails=[]; cls.students=[]
            for i in range(2):
                uid='28bit'+str(secrets.randbelow(900000)+100000); email=uid+'@cuchd.in'; cls.emails.append(email)
                c.execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'student')",('Portal fixture '+cls.suffix,email,generate_password_hash(cls.password))); user=c.lastrowid; cls.ids.append(user)
                c.execute('INSERT INTO student_profiles (user_id,university_uid,department_id,current_year,cgpa,graduation_year) VALUES (%s,%s,%s,3,8.5,%s)',(user,uid,cls.dep,datetime.now().year+2)); cls.students.append(c.lastrowid)
            cls.admin_email='portal-fixture-'+cls.suffix+'@example.test'
            c.execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'admin')",('Portal fixture administrator',cls.admin_email,generate_password_hash(cls.password))); cls.ids.append(c.lastrowid)

    @classmethod
    def tearDownClass(cls):
        with privileged() as c:
            for oid in cls.opportunities: c.execute("UPDATE opportunities SET listing_status='cancelled' WHERE opportunity_id=%s",(oid,))
            for uid in cls.ids: c.execute('UPDATE users SET is_active=FALSE WHERE user_id=%s',(uid,))

    def post(self,c,path,data=None,follow=False):
        c.get('/login')
        with c.session_transaction() as s: token=s['csrf']
        return c.post(path,data={**(data or {}),'csrf_token':token},follow_redirects=follow)

    def login(self,email):
        c=app.test_client(); r=self.post(c,'/login',{'identifier':email,'password':self.password})
        self.assertEqual(r.status_code,302)
        self.assertTrue(r.location.endswith('/admin/dashboard' if email==self.admin_email else '/student/dashboard'))
        return c

    def test_complete_workflow(self):
        student=self.login(self.emails[0]); other=self.login(self.emails[1]); admin=self.login(self.admin_email)
        title='Portal integration '+self.suffix
        values={'title':title,'description':'A test-only opportunity for verifying the real student and administrator workflow.','organization_id':self.org,'category_id':self.cat,'mode':'remote','location':'Test campus','application_deadline':(datetime.now()+timedelta(days=20)).isoformat(timespec='minutes'),'listing_status':'published','minimum_cgpa':'7','minimum_year':'2','maximum_year':'4','all_departments':'on','required_skills':str(self.skill),'documents':str(self.doc)}
        with self.subTest('opportunity creation'):
            self.assertIn(b'Opportunity saved',self.post(admin,'/admin/opportunities/new',values,True).data)
            with privileged() as c:
                c.execute('SELECT opportunity_id FROM opportunities WHERE title=%s',(title,)); oid=c.fetchone()['opportunity_id']; self.opportunities.append(oid)
            self.assertIn(b'Opportunity saved',self.post(admin,f'/admin/opportunities/{oid}/edit',values,True).data)
        with self.subTest('filtering and readiness'):
            for path in (f'/student/discover?q={self.suffix}',f'/student/discover?q={self.suffix}&category={self.cat}&department={self.dep}&skill={self.skill}&mode=remote&eligible=1&sort=readiness',f'/student/opportunities/{oid}'):
                r=student.get(path); self.assertEqual(r.status_code,200); self.assertIn(title.encode(),r.data)
            self.assertIn(b'Academic profile and skills updated',self.post(student,'/student/profile',{'department_id':self.dep,'current_year':3,'cgpa':8.5,'graduation_year':datetime.now().year+2,f'skill_{self.skill}':'advanced'},True).data)
        with self.subTest('save documents and planner'):
            self.assertIn(b'Opportunity saved',self.post(student,f'/student/opportunities/{oid}/save',follow=True).data)
            with privileged() as c:
                c.execute('SELECT application_id FROM applications WHERE student_id=%s AND opportunity_id=%s',(self.students[0],oid)); aid=c.fetchone()['application_id']
            self.assertIn(b'readiness updated',self.post(student,f'/student/applications/{aid}/documents',{'ready':str(self.doc)},True).data)
            self.assertIn(b'Preparation task added',self.post(student,f'/student/applications/{aid}/tasks',{'title':'Prepare test interview','due_date':(datetime.now()+timedelta(days=2)).date().isoformat()},True).data)
            with privileged() as c:
                c.execute('SELECT task_id FROM preparation_tasks WHERE application_id=%s',(aid,)); tid=c.fetchone()['task_id']
            self.assertEqual(self.post(student,f'/student/applications/{aid}/tasks/{tid}/toggle').status_code,302)
            self.assertIn(b'100% prepared',student.get(f'/student/applications/{aid}').data)
        with self.subTest('submission and duplicate prevention'):
            self.assertIn(b'Application submitted',self.post(student,f'/student/opportunities/{oid}/apply',follow=True).data)
            self.assertIn(b'already in your applications',self.post(student,f'/student/opportunities/{oid}/apply',follow=True).data)
            with privileged() as c:
                c.execute('SELECT COUNT(*) n FROM applications WHERE student_id=%s AND opportunity_id=%s',(self.students[0],oid)); self.assertEqual(c.fetchone()['n'],1)
        with self.subTest('all screens and role guards'):
            for client,paths in [(student,['/student/dashboard','/student/profile','/student/discover','/student/applications',f'/student/applications/{aid}']),(admin,['/admin/dashboard','/admin/opportunities','/admin/opportunities/new',f'/admin/opportunities/{oid}/edit','/admin/applications',f'/admin/applications/{aid}','/admin/database'])]:
                for path in paths:
                    with self.subTest(path=path): self.assertEqual(client.get(path).status_code,200)
            self.assertEqual(student.get('/admin/dashboard').status_code,403)
            self.assertEqual(admin.get('/student/dashboard').status_code,403)
            for table in ('users','student_profiles','opportunities','applications','application_status_history'):
                r=admin.get('/admin/database?table='+table); self.assertEqual(r.status_code,200); self.assertNotIn(b'$scrypt$',r.data)
        with self.subTest('IDOR'):
            for path in (f'/student/applications/{aid}',): self.assertEqual(other.get(path).status_code,404)
            for path,data in [(f'/student/applications/{aid}/withdraw',{}),(f'/student/applications/{aid}/documents',{'ready':str(self.doc)}),(f'/student/applications/{aid}/tasks',{'title':'Intruder','due_date':'2027-01-01'}),(f'/student/applications/{aid}/tasks/{tid}/toggle',{})]:
                self.assertEqual(self.post(other,path,data).status_code,404)
        with self.subTest('concurrent review and private notes'):
            def review(_): return self.post(self.login(self.admin_email),f'/admin/applications/{aid}',{'status':'under_review','note':'Private portal test note'}).status_code
            with ThreadPoolExecutor(max_workers=2) as pool: self.assertEqual(list(pool.map(review,range(2))),[302,302])
            r=student.get(f'/student/applications/{aid}'); self.assertIn(b'Under Review',r.data); self.assertNotIn(b'Private portal test note',r.data)
            with privileged() as c:
                c.execute("SELECT COUNT(*) n FROM application_status_history WHERE application_id=%s AND new_status='under_review'",(aid,)); self.assertEqual(c.fetchone()['n'],1)
                c.execute('SELECT COUNT(*) n FROM notifications WHERE application_id=%s',(aid,)); self.assertEqual(c.fetchone()['n'],1)
        with self.subTest('withdrawal and final states'):
            self.assertIn(b'Application withdrawn',self.post(student,f'/student/applications/{aid}/withdraw',follow=True).data)
            self.assertIn(b'not allowed',self.post(admin,f'/admin/applications/{aid}',{'status':'selected'},True).data)
        with self.subTest('academic deadline and status restrictions'):
            for patch in ({'minimum_cgpa':'9.9'},{'application_deadline':(datetime.now()-timedelta(days=1)).isoformat(timespec='minutes')},{'listing_status':'closed'}):
                self.post(admin,f'/admin/opportunities/{oid}/edit',{**values,**patch})
                r=self.post(other,f'/student/opportunities/{oid}/apply')
                self.assertEqual(r.status_code,302)
                with other.session_transaction() as s:
                    self.assertTrue(any('blocked' in text or 'closed' in text for _,text in s.get('_flashes',[])))
        with self.subTest('CSRF new routes'):
            for path in (f'/student/opportunities/{oid}/apply',f'/student/applications/{aid}/documents',f'/admin/applications/{aid}','/admin/opportunities/new'):
                self.assertEqual(student.post(path).status_code,400)

    def test_portal_mutation_rate_limits(self):
        old_key=app.secret_key
        try:
            for email,path in ((self.emails[1],'/student/opportunities/2147483647/apply'),(self.admin_email,'/admin/applications/2147483647')):
                app.secret_key=secrets.token_hex(32)
                app.config.update(RATE_LIMIT_ENABLED=True,RATE_LIMIT_TEST_RULE=(2,60))
                client=self.login(email)
                responses=[self.post(client,path) for _ in range(3)]
                self.assertEqual([r.status_code for r in responses],[404,404,429])
                self.assertGreater(int(responses[-1].headers['Retry-After']),0)
        finally:
            app.secret_key=old_key
            app.config.update(RATE_LIMIT_ENABLED=False)
            app.config.pop('RATE_LIMIT_TEST_RULE',None)
