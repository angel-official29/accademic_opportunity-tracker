import math
from datetime import datetime,date
from flask import Blueprint,g,request,render_template,redirect,url_for,flash,abort
from mysql.connector import IntegrityError
from database import query,execute,transaction
from security import role_required
from portal_services import OPPORTUNITIES,enrich,references,LABELS

bp=Blueprint('student',__name__,url_prefix='/student')


@bp.before_request
@role_required('student')
def protect():
    g.student=query('SELECT p.*,d.department_name FROM student_profiles p JOIN departments d ON d.department_id=p.department_id WHERE p.user_id=%s',(g.user['user_id'],),one=True)


def require_profile():
    if not g.student:
        flash('Complete your academic profile first.','error')
        return redirect(url_for('profile_setup'))


def opportunity(oid):
    row=query(OPPORTUNITIES+' WHERE o.opportunity_id=%s',(oid,),one=True)
    if not row: abort(404)
    return enrich(g.student,[row])[0]


@bp.get('/dashboard')
def dashboard():
    rows=enrich(g.student,query(OPPORTUNITIES+" WHERE o.listing_status='published' AND o.application_deadline>=NOW() ORDER BY o.application_deadline"))
    sid=g.student['student_id'] if g.student else None
    counts=query("SELECT COUNT(*) total,COALESCE(SUM(application_status IN ('applied','under_review','shortlisted')),0) active,COALESCE(SUM(application_status IN ('saved','preparing')),0) saved FROM applications WHERE student_id=%s",(sid,),one=True)
    recent=query('SELECT a.*,o.title FROM applications a JOIN opportunities o ON o.opportunity_id=a.opportunity_id WHERE a.student_id=%s ORDER BY a.updated_at DESC LIMIT 5',(sid,))
    alerts=query('SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 5',(g.user['user_id'],))
    recommendations=sorted(rows,key=lambda o:(o['readiness']['eligible'],o['readiness']['score']),reverse=True)[:3]
    completion=round(sum(g.student.get(k) is not None for k in ('department_id','current_year','cgpa','graduation_year'))*25) if g.student else 0
    return render_template('portal/dashboard.html',opportunities=recommendations,deadlines=rows[:5],counts=counts,recent=recent,alerts=alerts,completion=completion,labels=LABELS)


@bp.get('/discover')
def discover():
    clauses=["o.listing_status='published'",'o.application_deadline>=NOW()']; params=[]
    keyword=request.args.get('q','').strip()[:150]
    if keyword:
        clauses.append('(o.title LIKE %s OR o.description LIKE %s OR org.organization_name LIKE %s)'); params.extend([f'%{keyword}%']*3)
    for key,clause in [('category','o.category_id=%s'),('department','(e.all_departments_allowed=TRUE OR EXISTS (SELECT 1 FROM opportunity_departments od WHERE od.opportunity_id=o.opportunity_id AND od.department_id=%s))'),('skill','EXISTS (SELECT 1 FROM opportunity_skills os WHERE os.opportunity_id=o.opportunity_id AND os.skill_id=%s)')]:
        value=request.args.get(key,'')
        if value.isascii() and value.isdigit() and len(value)<=10:
            clauses.append(clause); params.append(int(value))
    mode=request.args.get('mode')
    if mode in ('remote','hybrid','onsite'): clauses.append('o.mode=%s'); params.append(mode)
    if request.args.get('deadline'):
        try:
            end=datetime.combine(date.fromisoformat(request.args['deadline']),datetime.max.time())
            clauses.append('o.application_deadline<=%s'); params.append(end)
        except ValueError: flash('Choose a valid deadline date.','error')
    rows=enrich(g.student,query(OPPORTUNITIES+' WHERE '+' AND '.join(clauses)+' ORDER BY o.application_deadline',tuple(params)))
    if request.args.get('eligible'): rows=[o for o in rows if o['readiness']['eligible']]
    sort=request.args.get('sort')
    if sort in ('newest','readiness'): rows.sort(key=lambda o:o['created_at'] if sort=='newest' else o['readiness']['score'],reverse=True)
    return render_template('portal/discover.html',opportunities=rows,labels=LABELS,**references())


@bp.get('/opportunities/<int:oid>')
def detail(oid):
    o=opportunity(oid)
    if o['listing_status']!='published' and not o['application']: abort(404)
    return render_template('portal/detail.html',o=o,labels=LABELS)


def history(aid,old,new,note=None):
    execute('INSERT INTO application_status_history (application_id,old_status,new_status,changed_by,change_note) VALUES (%s,%s,%s,%s,%s)',(aid,old,new,g.user['user_id'],note))


def create_application(o,status):
    aid=execute('INSERT INTO applications (student_id,opportunity_id,application_status,applied_at) VALUES (%s,%s,%s,%s)',(g.student['student_id'],o['opportunity_id'],status,datetime.now() if status=='applied' else None))
    history(aid,None,status)
    for d in o['documents']:
        execute('INSERT INTO application_documents (application_id,document_type_id) VALUES (%s,%s)',(aid,d['document_type_id']))
    return aid


@bp.post('/opportunities/<int:oid>/<action>')
def save_apply(oid,action):
    if action not in ('save','apply'): abort(404)
    incomplete=require_profile()
    if incomplete: return incomplete
    try:
        with transaction():
            query('SELECT opportunity_id FROM opportunities WHERE opportunity_id=%s FOR UPDATE',(oid,),one=True)
            o=opportunity(oid)
            if o['listing_status']!='published' or o['application_deadline']<datetime.now():
                flash('This opportunity is closed or its deadline has passed.','error')
                return redirect(url_for('student.detail',oid=oid))
            if action=='apply' and not o['readiness']['eligible']:
                flash('Application blocked: '+o['readiness']['next_action'],'error')
                return redirect(url_for('student.detail',oid=oid))
            a=query('SELECT * FROM applications WHERE student_id=%s AND opportunity_id=%s FOR UPDATE',(g.student['student_id'],oid),one=True)
            if a:
                aid=a['application_id']
                if action=='apply' and a['application_status'] in ('saved','preparing'):
                    execute("UPDATE applications SET application_status='applied',applied_at=NOW() WHERE application_id=%s",(aid,))
                    history(aid,a['application_status'],'applied'); flash('Application submitted.','success')
                else: flash('This opportunity is already in your applications.','error' if action=='apply' else 'success')
            else:
                aid=create_application(o,'applied' if action=='apply' else 'saved')
                flash('Application submitted.' if action=='apply' else 'Opportunity saved. Track documents and preparation below.','success')
        return redirect(url_for('student.application',aid=aid))
    except IntegrityError:
        flash('This opportunity is already in your applications.','error')
        return redirect(url_for('student.applications'))


@bp.get('/applications')
def applications():
    sid=g.student['student_id'] if g.student else None
    rows=query('SELECT a.*,o.title,o.application_deadline,org.organization_name FROM applications a JOIN opportunities o ON o.opportunity_id=a.opportunity_id JOIN organizations org ON org.organization_id=o.organization_id WHERE a.student_id=%s ORDER BY a.updated_at DESC',(sid,))
    return render_template('portal/applications.html',applications=rows,labels=LABELS)


def owned_application(aid,lock=False):
    if not g.student: abort(404)
    a=query('SELECT * FROM applications WHERE application_id=%s AND student_id=%s'+(' FOR UPDATE' if lock else ''),(aid,g.student['student_id']),one=True)
    if not a: abort(404)
    return a


@bp.get('/applications/<int:aid>')
def application(aid):
    a=owned_application(aid)
    docs=query('SELECT ad.*,d.document_name FROM application_documents ad JOIN document_types d ON d.document_type_id=ad.document_type_id WHERE ad.application_id=%s',(aid,))
    tasks=query('SELECT * FROM preparation_tasks WHERE application_id=%s ORDER BY due_date,task_id',(aid,))
    changes=query('SELECT new_status,changed_at FROM application_status_history WHERE application_id=%s ORDER BY history_id',(aid,))
    return render_template('portal/application.html',a=a,o=opportunity(a['opportunity_id']),documents=docs,tasks=tasks,history=changes,labels=LABELS,today=datetime.now())


@bp.post('/applications/<int:aid>/withdraw')
def withdraw(aid):
    with transaction():
        a=owned_application(aid,True)
        if a['application_status'] not in ('applied','under_review','shortlisted'):
            flash('This application cannot be withdrawn in its current state.','error')
        else:
            execute("UPDATE applications SET application_status='withdrawn' WHERE application_id=%s",(aid,)); history(aid,a['application_status'],'withdrawn'); flash('Application withdrawn.','success')
    return redirect(url_for('student.application',aid=aid))


@bp.post('/applications/<int:aid>/documents')
def documents(aid):
    with transaction():
        owned_application(aid,True)
        docs=query('SELECT document_type_id FROM application_documents WHERE application_id=%s',(aid,))
        for d in docs:
            state='ready' if str(d['document_type_id']) in request.form.getlist('ready') else 'pending'
            execute("UPDATE application_documents SET document_status=%s WHERE application_id=%s AND document_type_id=%s AND document_status IN ('pending','ready','needs_update')",(state,aid,d['document_type_id']))
    flash('Self-reported document readiness updated. No files were uploaded.','success')
    return redirect(url_for('student.application',aid=aid))


@bp.post('/applications/<int:aid>/tasks')
def add_task(aid):
    owned_application(aid)
    try:
        title=request.form.get('title','').strip(); due=date.fromisoformat(request.form.get('due_date',''))
        if not 2<=len(title)<=150: raise ValueError()
        with transaction(): execute('INSERT INTO preparation_tasks (application_id,task_title,due_date) VALUES (%s,%s,%s)',(aid,title,due))
        flash('Preparation task added.','success')
    except (ValueError,IntegrityError): flash('Enter a valid unique task title and due date.','error')
    return redirect(url_for('student.application',aid=aid))


@bp.post('/applications/<int:aid>/tasks/<int:tid>/toggle')
def toggle_task(aid,tid):
    with transaction():
        owned_application(aid,True)
        execute("UPDATE preparation_tasks SET task_status=IF(task_status='completed','pending','completed'),completed_at=IF(task_status='completed',NOW(),NULL) WHERE task_id=%s AND application_id=%s",(tid,aid))
    return redirect(url_for('student.application',aid=aid))


@bp.route('/profile',methods=['GET','POST'])
def profile():
    incomplete=require_profile()
    if incomplete: return incomplete
    ref=references()
    if request.method=='POST':
        try:
            dep=int(request.form.get('department_id','0')); year=int(request.form.get('current_year','0'))
            cgpa=float(request.form['cgpa']) if request.form.get('cgpa') else None
            grad=int(request.form['graduation_year']) if request.form.get('graduation_year') else None
            if dep not in {d['department_id'] for d in ref['departments']} or not 1<=year<=4 or (cgpa is not None and (not math.isfinite(cgpa) or not 0<=cgpa<=10)) or (grad is not None and not date.today().year<=grad<=date.today().year+10): raise ValueError()
            levels={}
            for s in ref['skills']:
                value=request.form.get(f'skill_{s["skill_id"]}','')
                if value not in ('','beginner','intermediate','advanced'): raise ValueError()
                if value: levels[s['skill_id']]=value
            with transaction():
                execute('UPDATE student_profiles SET department_id=%s,current_year=%s,cgpa=%s,graduation_year=%s WHERE student_id=%s',(dep,year,cgpa,grad,g.student['student_id']))
                execute('DELETE FROM student_skills WHERE student_id=%s',(g.student['student_id'],))
                for sid,level in levels.items(): execute('INSERT INTO student_skills (student_id,skill_id,proficiency_level,is_verified) VALUES (%s,%s,%s,FALSE)',(g.student['student_id'],sid,level))
            flash('Academic profile and skills updated.','success'); return redirect(url_for('student.dashboard'))
        except ValueError: flash('Check department, academic values and skill levels.','error')
    levels={s['skill_id']:s['proficiency_level'] for s in query('SELECT skill_id,proficiency_level FROM student_skills WHERE student_id=%s',(g.student['student_id'],))}
    return render_template('portal/profile.html',profile=g.student,levels=levels,**ref)
