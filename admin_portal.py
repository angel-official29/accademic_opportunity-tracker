from datetime import datetime
from urllib.parse import urlsplit
import math
from flask import Blueprint,g,request,render_template,redirect,url_for,flash,abort
from database import query,execute,transaction
from security import role_required
from portal_services import OPPORTUNITIES,enrich,references,STATES,TRANSITIONS,LABELS

bp=Blueprint('admin',__name__,url_prefix='/admin')


@bp.before_request
@role_required('admin')
def protect(): pass


@bp.get('/dashboard')
def dashboard():
    counts={'Students':query("SELECT COUNT(*) n FROM users WHERE role='student' AND is_active=TRUE",one=True)['n'],
        'Open opportunities':query("SELECT COUNT(*) n FROM opportunities WHERE listing_status='published' AND application_deadline>=NOW()",one=True)['n'],
        'Submitted applications':query("SELECT COUNT(*) n FROM applications WHERE application_status NOT IN ('saved','preparing')",one=True)['n'],
        'Pending reviews':query("SELECT COUNT(*) n FROM applications WHERE application_status IN ('applied','under_review')",one=True)['n']}
    statuses=query('SELECT application_status,COUNT(*) n FROM applications GROUP BY application_status')
    categories=query('SELECT c.category_name,COUNT(o.opportunity_id) n FROM opportunity_categories c LEFT JOIN opportunities o ON o.category_id=c.category_id GROUP BY c.category_id ORDER BY n DESC')
    recent=query("SELECT a.*,u.full_name,o.title FROM applications a JOIN student_profiles p ON p.student_id=a.student_id JOIN users u ON u.user_id=p.user_id JOIN opportunities o ON o.opportunity_id=a.opportunity_id WHERE a.application_status NOT IN ('saved','preparing') ORDER BY a.updated_at DESC LIMIT 8")
    deadlines=query("SELECT opportunity_id,title,application_deadline FROM opportunities WHERE listing_status='published' AND application_deadline>=NOW() ORDER BY application_deadline LIMIT 5")
    return render_template('portal/admin_dashboard.html',counts=counts,statuses=statuses,categories=categories,recent=recent,deadlines=deadlines,labels=LABELS)


@bp.get('/opportunities')
def opportunities():
    return render_template('portal/admin_opportunities.html',opportunities=query(OPPORTUNITIES+' ORDER BY o.updated_at DESC'))


@bp.route('/opportunities/new',methods=['GET','POST'])
@bp.route('/opportunities/<int:oid>/edit',methods=['GET','POST'])
def edit_opportunity(oid=None):
    ref=references(); o=query(OPPORTUNITIES+' WHERE o.opportunity_id=%s',(oid,),one=True) if oid else {}
    if oid and not o: abort(404)
    selected={key:[] for key in ('departments','required_skills','preferred_skills','documents')}
    if oid:
        selected['departments']=[r['department_id'] for r in query('SELECT department_id FROM opportunity_departments WHERE opportunity_id=%s',(oid,))]
        for s in query('SELECT skill_id,requirement_type FROM opportunity_skills WHERE opportunity_id=%s',(oid,)):
            selected[s['requirement_type']+'_skills'].append(s['skill_id'])
        selected['documents']=[d['document_type_id'] for d in query('SELECT document_type_id FROM opportunity_documents WHERE opportunity_id=%s AND is_mandatory=TRUE',(oid,))]
    if request.method=='POST':
        try:
            title=request.form.get('title','').strip(); description=request.form.get('description','').strip(); location=request.form.get('location','').strip()
            if not 3<=len(title)<=180 or not 20<=len(description)<=20000 or len(location)>150: raise ValueError('Check title description and location lengths.')
            org=int(request.form.get('organization_id','0')); cat=int(request.form.get('category_id','0'))
            if org not in {r['organization_id'] for r in ref['organizations']} or cat not in {r['category_id'] for r in ref['categories']}: raise ValueError('Choose an existing organization and category.')
            deadline=datetime.fromisoformat(request.form.get('application_deadline',''))
            if deadline.tzinfo: raise ValueError('Use local date and time without a timezone offset.')
            start=datetime.strptime(request.form['start_date'],'%Y-%m-%d').date() if request.form.get('start_date') else None
            end=datetime.strptime(request.form['end_date'],'%Y-%m-%d').date() if request.form.get('end_date') else None
            if start and end and end<start: raise ValueError('End date must follow start date.')
            mode=request.form.get('mode'); status=request.form.get('listing_status')
            if mode not in ('remote','hybrid','onsite') or status not in ('draft','published','closed','cancelled'): raise ValueError('Choose a valid mode and listing status.')
            cgpa=float(request.form.get('minimum_cgpa','0')); lo=int(request.form.get('minimum_year','1')); hi=int(request.form.get('maximum_year','4'))
            if not math.isfinite(cgpa) or not 0<=cgpa<=10 or not 1<=lo<=hi<=4: raise ValueError('Check minimum CGPA and academic year limits.')
            stipend=float(request.form['stipend']) if request.form.get('stipend') else None
            if stipend is not None and (not math.isfinite(stipend) or not 0<=stipend<=99999999.99): raise ValueError('Enter a valid nonnegative stipend.')
            external=request.form.get('application_url','').strip()
            if external and (len(external)>500 or urlsplit(external).scheme not in ('https','http') or not urlsplit(external).netloc): raise ValueError('External application URL must be a valid http or https address.')
            choices={}
            for key,rows,pk in [('departments',ref['departments'],'department_id'),('required_skills',ref['skills'],'skill_id'),('preferred_skills',ref['skills'],'skill_id'),('documents',ref['documents'],'document_type_id')]:
                ids=set(map(int,request.form.getlist(key)))
                if not ids.issubset({r[pk] for r in rows}): raise ValueError('Unknown requirement selection.')
                choices[key]=ids
            if choices['required_skills'] & choices['preferred_skills']: raise ValueError('A skill cannot be both required and preferred.')
            all_departments='all_departments' in request.form
            if not all_departments and not choices['departments']: raise ValueError('Select an allowed department or allow all departments.')
            with transaction():
                values=(org,cat,title,description,mode,location,stipend,external or None,deadline,start,end,status)
                if oid:
                    execute('UPDATE opportunities SET organization_id=%s,category_id=%s,title=%s,description=%s,mode=%s,location=%s,stipend=%s,application_url=%s,application_deadline=%s,start_date=%s,end_date=%s,listing_status=%s WHERE opportunity_id=%s',values+(oid,))
                else:
                    oid=execute('INSERT INTO opportunities (organization_id,category_id,title,description,mode,location,stipend,application_url,application_deadline,start_date,end_date,listing_status,created_by,is_campus_managed) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)',values+(g.user['user_id'],))
                execute('INSERT INTO eligibility_requirements (opportunity_id,minimum_cgpa,minimum_year,maximum_year,all_departments_allowed) VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE minimum_cgpa=%s,minimum_year=%s,maximum_year=%s,all_departments_allowed=%s',(oid,cgpa,lo,hi,all_departments,cgpa,lo,hi,all_departments))
                for table in ('opportunity_departments','opportunity_skills','opportunity_documents'):
                    execute(f'DELETE FROM {table} WHERE opportunity_id=%s',(oid,))
                for dep in choices['departments']: execute('INSERT INTO opportunity_departments VALUES (%s,%s)',(oid,dep))
                for key,kind in [('required_skills','required'),('preferred_skills','preferred')]:
                    for sid in choices[key]: execute('INSERT INTO opportunity_skills VALUES (%s,%s,%s)',(oid,sid,kind))
                for doc in choices['documents']: execute('INSERT INTO opportunity_documents VALUES (%s,%s,TRUE)',(oid,doc))
            flash('Opportunity saved.','success'); return redirect(url_for('admin.opportunities'))
        except (ValueError,TypeError) as error:
            message=str(error)
            flash('Check all numeric values and dates.' if message.startswith(('invalid literal','Invalid isoformat','could not convert','time data')) else message,'error')
    return render_template('portal/admin_opportunity_form.html',o=o,selected=selected,**ref)


@bp.get('/applications')
def applications():
    clauses=["a.application_status NOT IN ('saved','preparing')"]; params=[]
    if request.args.get('status') in STATES:
        clauses=['a.application_status=%s']; params=[request.args['status']]
    keyword=request.args.get('q','').strip()[:150]
    if keyword:
        clauses.append('(u.full_name LIKE %s OR p.university_uid LIKE %s OR o.title LIKE %s)'); params.extend([f'%{keyword}%']*3)
    rows=query('SELECT a.*,u.full_name,p.university_uid,o.title FROM applications a JOIN student_profiles p ON p.student_id=a.student_id JOIN users u ON u.user_id=p.user_id JOIN opportunities o ON o.opportunity_id=a.opportunity_id WHERE '+' AND '.join(clauses)+' ORDER BY a.updated_at DESC',tuple(params))
    return render_template('portal/admin_applications.html',applications=rows,labels=LABELS,states=STATES)


@bp.route('/applications/<int:aid>',methods=['GET','POST'])
def review(aid):
    a=query('SELECT a.*,p.user_id FROM applications a JOIN student_profiles p ON p.student_id=a.student_id WHERE a.application_id=%s',(aid,),one=True)
    if not a: abort(404)
    if request.method=='POST':
        new=request.form.get('status'); note=request.form.get('note','').strip()
        with transaction():
            current=query('SELECT application_status FROM applications WHERE application_id=%s FOR UPDATE',(aid,),one=True)['application_status']
            if new not in TRANSITIONS[current] or len(note)>255:
                flash('This status transition is not allowed, or the note is too long.','error')
            else:
                execute('UPDATE applications SET application_status=%s WHERE application_id=%s',(new,aid))
                execute('INSERT INTO application_status_history (application_id,old_status,new_status,changed_by,change_note) VALUES (%s,%s,%s,%s,%s)',(aid,current,new,g.user['user_id'],note))
                execute("INSERT INTO notifications (user_id,notification_type,title,message,opportunity_id,application_id) VALUES (%s,'application_status',%s,%s,%s,%s)",(a['user_id'],'Application status updated',f'Your application is now {LABELS[new]}.',a['opportunity_id'],aid))
                flash('Status updated, history recorded and student notified.','success')
        return redirect(url_for('admin.review',aid=aid))
    profile=query('SELECT p.*,u.full_name,u.email,d.department_name FROM student_profiles p JOIN users u ON u.user_id=p.user_id JOIN departments d ON d.department_id=p.department_id WHERE p.user_id=%s',(a['user_id'],),one=True)
    o=enrich(profile,[query(OPPORTUNITIES+' WHERE o.opportunity_id=%s',(a['opportunity_id'],),one=True)])[0]
    changes=query('SELECT h.*,u.full_name FROM application_status_history h JOIN users u ON u.user_id=h.changed_by WHERE h.application_id=%s ORDER BY h.history_id',(aid,))
    docs=query('SELECT ad.*,d.document_name FROM application_documents ad JOIN document_types d ON d.document_type_id=ad.document_type_id WHERE ad.application_id=%s',(aid,))
    skills=query('SELECT s.skill_name,ss.proficiency_level,ss.is_verified FROM student_skills ss JOIN skills s ON s.skill_id=ss.skill_id WHERE ss.student_id=%s',(a['student_id'],))
    return render_template('portal/admin_review.html',a=a,profile=profile,o=o,history=changes,documents=docs,skills=skills,transitions=TRANSITIONS[a['application_status']],labels=LABELS)


SCHEMA_TABLES=('departments','users','student_profiles','skills','student_skills','organizations','opportunity_categories','opportunities','eligibility_requirements','opportunity_departments','opportunity_skills','applications','application_status_history','document_types','opportunity_documents','application_documents','preparation_tasks','student_interests','notifications','auth_sessions','security_rate_limits')


@bp.get('/database')
def database_browser():
    table=request.args.get('table','opportunities')
    if table not in SCHEMA_TABLES: abort(404)
    columns=query('SELECT COLUMN_NAME,DATA_TYPE,IS_NULLABLE,COLUMN_KEY FROM information_schema.columns WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION',(table,))
    links=query('SELECT COLUMN_NAME,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME FROM information_schema.key_column_usage WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND REFERENCED_TABLE_NAME IS NOT NULL',(table,))
    # Schema-only evidence; hashes, credentials and real student rows are never rendered.
    return render_template('portal/database.html',table=table,tables=SCHEMA_TABLES,columns=columns,links=links)
