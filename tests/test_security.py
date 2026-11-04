"""Defensive tests against the Documents schema, using generated fixture accounts only."""
import os
import re
import secrets
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from dotenv import dotenv_values
from flask import Flask
from werkzeug.security import generate_password_hash,check_password_hash
import mysql.connector
from app import app
from security import configure,identity

ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def privileged():
    e=dotenv_values(ROOT/'.migration.env')
    db=mysql.connector.connect(host=e['DB_HOST'],port=int(e.get('DB_PORT','3306')),user=e['DB_USER'],password=e['DB_PASSWORD'],database=e['DB_NAME'])
    c=db.cursor(dictionary=True)
    try:
        yield c
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        c.close()
        db.close()


class AnonymousSecurityTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True,RATE_LIMIT_ENABLED=False)
        self.c=app.test_client()

    def test_csrf_missing_unicode_oversized_all_routes(self):
        self.c.get('/login')
        for path in ('/register','/login','/logout','/profile/setup'):
            for token in ('','invalid','\u00e9','x'*129):
                with self.subTest(path=path):
                    self.assertEqual(self.c.post(path,data={'csrf_token':token}).status_code,400)
        for method in ('PUT','PATCH','DELETE'):
            self.assertEqual(self.c.open('/profile/setup',method=method).status_code,400)

    def test_headers_errors_and_get_logout(self):
        for path in ('/','/login','/register','/not-found'):
            response=self.c.get(path)
            for key in ('Content-Security-Policy','Permissions-Policy','X-Frame-Options','Referrer-Policy','X-Content-Type-Options'):
                self.assertIn(key,response.headers)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertNotIn('Strict-Transport-Security',response.headers)
            self.assertNotIn(b'Traceback',response.data)
        self.assertFalse(app.debug)
        self.assertEqual(self.c.get('/logout').status_code,405)
        self.assertEqual(self.c.get('/profile/setup').status_code,302)
        self.assertEqual(self.c.get('/database-test').status_code,302)

    def test_host_and_request_limits(self):
        self.assertEqual(self.c.get('/',headers={'Host':'evil.example'}).status_code,400)
        r=self.c.post('/login',data='x'*(1024*1024+1),content_type='application/x-www-form-urlencoded')
        self.assertEqual(r.status_code,413)

    def test_template_csrf_and_xss_sinks(self):
        for path in (ROOT/'templates').glob('*.html'):
            text=path.read_text(encoding='utf-8')
            self.assertNotIn('|safe',text)
            self.assertNotIn('style=',text)
            for form in re.findall(r'<form\b.*?</form>',text,re.S|re.I):
                if 'method="post"' in form.lower():
                    self.assertIn('name="csrf_token"',form)
        js=ROOT/'static/js/app.js'
        if js.exists():
            self.assertNotIn('innerHTML',js.read_text(encoding='utf-8'))

    def test_identity_normalization_and_mismatch(self):
        self.assertEqual(identity(' 25BIT10108 ','25BIT10108@CUCHD.IN'),('25bit10108','25bit10108@cuchd.in'))
        for uid,email in [('bad','bad@cuchd.in'),('25bit10108','wrong@cuchd.in'),('25bit10108','25bit10108@gmail.com'),('\u0662\u0665bit10108','\u0662\u0665bit10108@cuchd.in')]:
            with self.assertRaises(ValueError):
                identity(uid,email)

    def test_production_guards_and_https_cookie(self):
        e={'APP_ENV':'production','DB_USER':'cu_documents','TRUSTED_HOSTS':'tracker.example.test','VERCEL_URL':'deployment.example.vercel.app'}
        with patch.dict(os.environ,e):
            a=Flask('production-test')
            a.secret_key=secrets.token_hex(32)
            a.template_folder=str(ROOT/'templates')
            configure(a)

            a.config.update(TESTING=True,RATE_LIMIT_ENABLED=False)
            a.add_url_rule('/','home',lambda:'ok')
            a.add_url_rule('/login','login',lambda:'login')
            a.add_url_rule('/register','register',lambda:'register')
            c=a.test_client()
            self.assertEqual(c.get('/',base_url='http://tracker.example.test').status_code,400)
            r=c.get('/',base_url='https://tracker.example.test')
            self.assertEqual(r.status_code,200)
            self.assertEqual(c.get('/',base_url='https://deployment.example.vercel.app').status_code,200)
            self.assertIn('Strict-Transport-Security',r.headers)
            for flag in ('Secure','HttpOnly','SameSite=Lax'):
                self.assertIn(flag,r.headers['Set-Cookie'])
            self.assertEqual(c.get('/',base_url='https://evil.example').status_code,400)
        for override in ({'DB_USER':'root'},{'TRUSTED_HOSTS':''}):
            with patch.dict(os.environ,{**e,**override}),self.assertRaises(RuntimeError):
                a=Flask('invalid-production')
                a.secret_key=secrets.token_hex(32)
                configure(a)
        with self.assertRaises(RuntimeError):
            a=Flask('weak-secret')
            a.secret_key='replace-with-placeholder'
            configure(a)

    def test_safe_database_and_unexpected_errors(self):
        c=self.c
        c.get('/login')
        with c.session_transaction() as s:
            token=s['csrf']
        payload={'identifier':'25bit10108@cuchd.in','password':'invalid','csrf_token':token}
        for error,status in ((mysql.connector.DatabaseError('SENSITIVE-DO-NOT-PRINT'),503),(RuntimeError('SENSITIVE-DO-NOT-PRINT'),500)):
            with patch('app.query',side_effect=error),self.assertLogs(app.logger,level='ERROR') as captured:
                response=c.post('/login',data=payload)
            self.assertEqual(response.status_code,status)
            self.assertNotIn(b'SENSITIVE-DO-NOT-PRINT',response.data)
            self.assertNotIn('SENSITIVE-DO-NOT-PRINT',' '.join(captured.output))
            self.assertNotIn(b'Traceback',response.data)


@unittest.skipUnless(os.getenv('RUN_MYSQL_TESTS')=='1','Opt in with RUN_MYSQL_TESTS=1; requires migrated local database')
class DatabaseSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True,RATE_LIMIT_ENABLED=False)
        cls.password=secrets.token_urlsafe(20)
        cls.users=[]
        with privileged() as c:
            c.execute('SELECT department_id FROM departments LIMIT 1')
            cls.dep=c.fetchone()['department_id']

    @classmethod
    def tearDownClass(cls):
        with privileged() as c:
            for user_id in cls.users:
                c.execute('UPDATE users SET is_active=FALSE WHERE user_id=%s',(user_id,))

    def user(self,role='student',name='Security audit fixture'):
        uid='29bit'+str(secrets.randbelow(900000)+100000)
        email=uid+'@cuchd.in' if role=='student' else 'audit-'+secrets.token_hex(8)+'@example.test'
        with privileged() as c:
            c.execute('INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,%s)',(name,email,generate_password_hash(self.password),role))
            user_id=c.lastrowid
        self.users.append(user_id)
        return uid,email,user_id

    def post(self,c,path,data=None,follow=False,**kwargs):
        c.get('/login')
        with c.session_transaction() as s:
            token=s['csrf']
        return c.post(path,data={**(data or {}),'csrf_token':token},follow_redirects=follow,**kwargs)

    def login(self,email,password=None):
        c=app.test_client()
        r=self.post(c,'/login',{'identifier':email,'password':password or self.password})
        self.assertEqual(r.status_code,302)
        return c

    def test_registration_validation_hash_uniqueness_and_role(self):
        uid='28bit'+str(secrets.randbelow(900000)+100000)
        email=uid+'@cuchd.in'
        payload={'full_name':'Registration audit fixture','university_uid':uid.upper(),'email':email.upper(),'password':self.password,'confirm_password':self.password,'role':'admin','is_active':'0'}
        c=app.test_client()
        for change in ({'email':'wrong@cuchd.in'},{'email':uid+'@gmail.com'},{'password':'short','confirm_password':'short'},{'confirm_password':'wrong'}):
            r=self.post(c,'/register',{**payload,**change},True)
            self.assertNotIn(b'Account created successfully',r.data)
        r=self.post(c,'/register',payload,True)
        self.assertIn(b'Account created successfully',r.data)
        with privileged() as db:
            db.execute('SELECT user_id,email,password_hash,role,is_active FROM users WHERE email=%s',(email,))
            u=db.fetchone()
            self.users.append(u['user_id'])
            self.assertEqual(u['email'],email)
            self.assertEqual(u['role'],'student')
            self.assertTrue(u['is_active'])
            self.assertTrue(check_password_hash(u['password_hash'],self.password))
            self.assertNotEqual(u['password_hash'],self.password)
        self.assertIn(b'already registered',self.post(c,'/register',payload,True).data)
        # UID login also works before academic profile completion.
        self.assertEqual(self.post(c,'/login',{'identifier':uid.upper(),'password':self.password}).status_code,302)

    def test_login_injection_wrong_password_and_inactive(self):
        uid,email,user_id=self.user()
        c=app.test_client()
        for identifier in ("' OR 1=1 --",email,'no-such-account'):
            r=self.post(c,'/login',{'identifier':identifier,'password':'wrong-password'},True)
            self.assertIn(b'Invalid email or password',r.data)
            with c.session_transaction() as s:
                self.assertNotIn('user_id',s)
        c=self.login(email.upper())
        with privileged() as db:
            db.execute('UPDATE users SET is_active=FALSE WHERE user_id=%s',(user_id,))
        self.assertEqual(c.get('/profile/setup').status_code,302)
        self.assertIn(b'Invalid email or password',self.post(c,'/login',{'identifier':email,'password':self.password},True).data)

    def test_logout_replay_rotation_and_session_contents(self):
        _,email,_=self.user()
        c=app.test_client()
        c.get('/login')
        with c.session_transaction() as s:
            old=s['csrf']
        self.post(c,'/login',{'email':email,'password':self.password})
        cookie=c.get_cookie('session').value
        with c.session_transaction() as s:
            self.assertNotEqual(s['csrf'],old)
            self.assertNotIn('role',s)
            self.assertNotIn('full_name',s)
            self.assertNotIn('password',s)
        self.post(c,'/logout')
        replay=app.test_client()
        replay.set_cookie('session',cookie)
        self.assertEqual(replay.get('/profile/setup').status_code,302)

    def test_role_checks_and_diagnostic_metadata(self):
        _,email,_=self.user()
        c=self.login(email)
        self.assertEqual(c.get('/database-test').status_code,403)
        _,admin_email,admin_id=self.user('admin')
        a=self.login(admin_email)
        self.assertEqual(a.get('/profile/setup').status_code,403)
        r=a.get('/database-test')
        self.assertEqual(r.status_code,200)
        self.assertNotIn(b'tables',r.data)
        with privileged() as db:
            db.execute("UPDATE users SET role='student' WHERE user_id=%s",(admin_id,))
        self.assertEqual(a.get('/database-test').status_code,403)

    def test_profile_validation_uid_and_ownership(self):
        uid,email,user_id=self.user()
        _,_,other_id=self.user()
        c=self.login(email)
        payload={'university_uid':uid,'department_id':self.dep,'current_year':2,'cgpa':'8.25','graduation_year':datetime.now().year+2,'user_id':other_id,'role':'admin'}
        for change in ({'university_uid':'25bit10108'},{'current_year':'0'},{'current_year':'5'},{'cgpa':'NaN'},{'cgpa':'Infinity'},{'cgpa':'11'},{'department_id':'2147483647'},{'graduation_year':'bad'}):
            self.assertNotIn(b'Academic profile completed successfully',self.post(c,'/profile/setup',{**payload,**change},True).data)
        self.assertIn(b'Academic profile completed successfully',self.post(c,'/profile/setup',payload,True).data)
        with privileged() as db:
            db.execute('SELECT user_id,university_uid FROM student_profiles WHERE user_id IN (%s,%s)',(user_id,other_id))
            rows=db.fetchall()
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['user_id'],user_id)
            self.assertEqual(rows[0]['university_uid'],uid)

    def test_concurrent_profile_and_registration(self):
        uid,email,user_id=self.user()
        def submit(_):
            c=self.login(email)
            return self.post(c,'/profile/setup',{'university_uid':uid,'department_id':self.dep,'current_year':2,'cgpa':8,'graduation_year':datetime.now().year+2}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,range(2)))
            self.assertTrue(all(result in (200,302) for result in results))
            self.assertIn(302,results)
        with privileged() as db:
            db.execute('SELECT COUNT(*) n FROM student_profiles WHERE user_id=%s',(user_id,))
            self.assertEqual(db.fetchone()['n'],1)
        uid='27bit'+str(secrets.randbelow(900000)+100000)
        email=uid+'@cuchd.in'
        def register(_):
            return self.post(app.test_client(),'/register',{'full_name':'Concurrent audit fixture','university_uid':uid,'email':email,'password':self.password,'confirm_password':self.password}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(register,range(2)))
            self.assertEqual(sorted(results),[200,302])
        with privileged() as db:
            db.execute('SELECT user_id FROM users WHERE email=%s',(email,))
            rows=db.fetchall()
            self.assertEqual(len(rows),1)
            self.users.append(rows[0]['user_id'])

    def test_stored_and_reflected_xss(self):
        payload='<script>alert("audit")</script>'
        _,email,_=self.user(name=payload)
        c=self.login(email)
        self.assertNotIn(payload.encode(),c.get('/',follow_redirects=True).data)
        self.assertNotIn(b'<script>alert(1)</script>',c.get('/login?email=%3Cscript%3Ealert(1)%3C/script%3E').data)
        # Flash text is an actual user-input rendering sink.
        with c.session_transaction() as s:
            s['_flashes']=[('error',payload)]
        r=c.get('/',follow_redirects=True)
        self.assertIn(b'&lt;script&gt;',r.data)
        self.assertNotIn(payload.encode(),r.data)

    def test_shared_rate_limits(self):
        app.config.update(RATE_LIMIT_ENABLED=True,RATE_LIMIT_TEST_RULE=(2,60))
        try:
            for endpoint,payload in (('/login',{'identifier':'rate-'+secrets.token_hex(5),'password':'invalid'}),('/register',{'university_uid':'invalid'})):
                # Distinct real test IP per scope; forwarding headers do not alter it.
                address='192.0.2.'+str(secrets.randbelow(200)+1)
                results=[]
                for i in range(3):
                    c=app.test_client()
                    results.append(self.post(c,endpoint,payload,headers={'X-Forwarded-For':f'198.51.100.{i}'},environ_overrides={'REMOTE_ADDR':address}))
                self.assertNotEqual(results[0].status_code,429)
                self.assertNotEqual(results[1].status_code,429)
                self.assertEqual(results[2].status_code,429)
                self.assertGreater(int(results[2].headers['Retry-After']),0)
        finally:
            app.config.update(RATE_LIMIT_ENABLED=False)
            app.config.pop('RATE_LIMIT_TEST_RULE',None)

    def test_database_permissions_and_history_triggers(self):
        from database import get_db_connection
        db=get_db_connection()
        c=db.cursor()
        try:
            c.execute('SELECT CURRENT_USER(),@@transaction_isolation')
            principal,isolation=c.fetchone()
            self.assertFalse(principal.startswith('root@'))
            self.assertEqual(isolation,'READ-COMMITTED')
            c.execute('SHOW GRANTS')
            grants=[r[0] for r in c.fetchall()]
            self.assertFalse(any('ALL PRIVILEGES' in x or 'DROP' in x or 'ALTER' in x or 'GRANT OPTION' in x for x in grants))
            with self.assertRaises(mysql.connector.Error):
                c.execute('UPDATE application_status_history SET change_note=change_note WHERE history_id=-1')
            db.rollback()
        finally:
            c.close()
            db.close()
        with privileged() as c:
            c.execute('SELECT TRIGGER_NAME FROM information_schema.triggers WHERE trigger_schema=DATABASE() AND EVENT_OBJECT_TABLE=%s',('application_status_history',))
            self.assertEqual({r['TRIGGER_NAME'] for r in c.fetchall()},{'audit_history_no_update','audit_history_no_delete'})


if __name__=='__main__':
    unittest.main()
