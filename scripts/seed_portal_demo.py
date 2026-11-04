"""Insert clearly fictional demonstration records, never replace existing user data."""
from pathlib import Path
from datetime import datetime,timedelta
import secrets
from dotenv import dotenv_values
from werkzeug.security import generate_password_hash
import mysql.connector

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'.report-demo.env'
    if path.exists():
        print('Existing report demo identities retained.'); return
    e=dotenv_values(ROOT/'.migration.env')
    db=mysql.connector.connect(host=e['DB_HOST'],port=int(e.get('DB_PORT','3306')),user=e['DB_USER'],password=e['DB_PASSWORD'],database=e['DB_NAME'])
    c=db.cursor(dictionary=True)
    admin_email='report-demo-admin@example.test'; uid='26bit990001'; email=uid+'@cuchd.in'
    admin_password,student_password=(secrets.token_urlsafe(24) for _ in range(2))
    try:
        c.execute('SELECT user_id FROM users WHERE email IN (%s,%s)',(admin_email,email))
        if c.fetchall(): raise SystemExit('A demo identity already exists. No accounts changed.')
        c.execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'admin')",('Demonstration Administrator',admin_email,generate_password_hash(admin_password))); admin_id=c.lastrowid
        c.execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'student')",('Demonstration Student',email,generate_password_hash(student_password))); user_id=c.lastrowid
        c.execute('SELECT department_id FROM departments ORDER BY department_id LIMIT 1'); dep=c.fetchone()['department_id']
        c.execute('INSERT INTO student_profiles (user_id,university_uid,department_id,current_year,cgpa,graduation_year) VALUES (%s,%s,%s,3,8.4,%s)',(user_id,uid,dep,datetime.now().year+2)); sid=c.lastrowid
        c.execute("SELECT skill_id FROM skills WHERE skill_name IN ('Python','SQL','Communication')")
        for skill in c.fetchall(): c.execute("INSERT INTO student_skills (student_id,skill_id,proficiency_level) VALUES (%s,%s,'intermediate')",(sid,skill['skill_id']))
        for name in ('Campus Innovation Lab Demo','Northstar Research Demo','Horizon Foundation Demo'):
            c.execute("INSERT INTO organizations (organization_name,organization_type) VALUES (%s,'other') ON DUPLICATE KEY UPDATE organization_name=organization_name",(name,))
        for category in ('Workshop','Academic Program'):
            c.execute('INSERT INTO opportunity_categories (category_name,description) VALUES (%s,%s) ON DUPLICATE KEY UPDATE category_name=category_name',(category,'Demonstration category'))
        c.execute('SELECT organization_id,organization_name FROM organizations'); orgs={r['organization_name']:r['organization_id'] for r in c.fetchall()}
        c.execute('SELECT category_id,category_name FROM opportunity_categories'); cats={r['category_name']:r['category_id'] for r in c.fetchall()}
        c.execute('SELECT skill_id,skill_name FROM skills'); skills={r['skill_name']:r['skill_id'] for r in c.fetchall()}
        c.execute('SELECT document_type_id,document_name FROM document_types'); documents={r['document_name']:r['document_type_id'] for r in c.fetchall()}
        records=[
          ('Campus Software Internship','Internship',7,2,4,14,['Python','SQL'],['Resume','NOC']),
          ('Academic Excellence Scholarship','Scholarship',8,1,4,21,[],['Marksheet','Statement of Purpose']),
          ('Sustainable Campus Research','Research',7.5,2,4,30,['Data Analysis','Research Writing'],['Resume','Statement of Purpose']),
          ('Build for Campus Hackathon','Hackathon',0,1,4,7,['Web Development'],['Identity Card','Portfolio']),
          ('Student Innovation Challenge','Competition',0,1,4,18,['Communication'],['Portfolio']),
          ('Undergraduate Research Fellowship','Fellowship',8,3,4,40,['Python','Research Writing'],['Resume','Marksheet']),
          ('SQL and Data Storytelling Workshop','Workshop',0,1,4,5,[],['Identity Card']),
          ('Interdisciplinary Summer School','Academic Program',7,1,4,50,['Communication'],['Statement of Purpose'])]
        first=None
        for i,(title,category,cgpa,lo,hi,days,needed,docs) in enumerate(records):
            c.execute('INSERT INTO opportunities (organization_id,category_id,title,description,mode,location,application_deadline,listing_status,created_by,is_campus_managed) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)',(list(orgs.values())[i%len(orgs)],cats[category],title+' Demo','Fictional demonstration listing for the Academic Opportunity Tracker. Students can use this record to test eligibility, document preparation, application submission and administrative review. It is not an actual advertised university opening.','hybrid' if i%2==0 else 'remote','Chandigarh University demonstration',datetime.now()+timedelta(days=days),'published',admin_id)); oid=c.lastrowid
            if first is None: first=oid
            c.execute('INSERT INTO eligibility_requirements VALUES (%s,%s,%s,%s,TRUE)',(oid,cgpa,lo,hi))
            for skill in needed:
                if skill in skills: c.execute("INSERT INTO opportunity_skills VALUES (%s,%s,'required')",(oid,skills[skill]))
            for name in docs:
                if name in documents: c.execute('INSERT INTO opportunity_documents VALUES (%s,%s,TRUE)',(oid,documents[name]))
        c.execute("INSERT INTO applications (student_id,opportunity_id,application_status,applied_at) VALUES (%s,%s,'under_review',NOW())",(sid,first)); aid=c.lastrowid
        for old,new,actor,note in [(None,'saved',user_id,None),('saved','applied',user_id,None),('applied','under_review',admin_id,'Demonstration application ready for review.')]:
            c.execute('INSERT INTO application_status_history (application_id,old_status,new_status,changed_by,change_note) VALUES (%s,%s,%s,%s,%s)',(aid,old,new,actor,note))
        c.execute('SELECT document_type_id FROM opportunity_documents WHERE opportunity_id=%s',(first,))
        for d in c.fetchall(): c.execute("INSERT INTO application_documents (application_id,document_type_id,document_status) VALUES (%s,%s,'ready')",(aid,d['document_type_id']))
        c.execute("INSERT INTO preparation_tasks (application_id,task_title,due_date,task_status,completed_at) VALUES (%s,%s,%s,'completed',NOW())",(aid,'Prepare a short project presentation',datetime.now()+timedelta(days=3)))
        db.commit()
        path.write_text(f"ADMIN_EMAIL={admin_email}\nADMIN_PASSWORD={admin_password}\nSTUDENT_EMAIL={email}\nSTUDENT_UID={uid}\nSTUDENT_PASSWORD={student_password}\nOPPORTUNITY_ID={first}\nAPPLICATION_ID={aid}\n",encoding='utf-8')
        print('Eight fictional opportunities and private demo accounts created. Credentials saved only in ignored .report-demo.env.')
    except Exception:
        db.rollback(); raise
    finally: c.close(); db.close()


if __name__=='__main__': main()
