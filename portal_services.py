"""Database-backed opportunity rules and batched student enrichment."""
from collections import defaultdict
from datetime import datetime
from database import query

OPPORTUNITIES='''SELECT o.*,org.organization_name,c.category_name,
 e.minimum_cgpa,e.minimum_year,e.maximum_year,e.all_departments_allowed
 FROM opportunities o JOIN organizations org ON org.organization_id=o.organization_id
 JOIN opportunity_categories c ON c.category_id=o.category_id
 LEFT JOIN eligibility_requirements e ON e.opportunity_id=o.opportunity_id'''
STATES=('saved','preparing','applied','under_review','shortlisted','selected','rejected','withdrawn')
TRANSITIONS={'applied':('under_review','shortlisted','rejected'), 'under_review':('shortlisted','selected','rejected'),
 'shortlisted':('selected','rejected'),'saved':(),'preparing':(),'selected':(),'rejected':(),'withdrawn':()}
LABELS={s:s.replace('_',' ').title() for s in STATES}


def assess(profile,o,allowed,skills,docs,own_skills,ready_docs,tasks,now=None):
    now=now or datetime.now()
    academic=[]; reasons=[]
    def rule(ok,yes,no,graded=True):
        reasons.append({'ok':bool(ok),'text':yes if ok else no})
        if graded: academic.append(bool(ok))
    p=profile or {}
    rule(bool(p.get('department_id') and p.get('current_year')),'Academic profile is available.','Complete your academic profile.')
    if not o.get('all_departments_allowed',True):
        rule(p.get('department_id') in allowed,'Your department is eligible.','Your department is not allowed.')
    minimum=float(o.get('minimum_cgpa') or 0)
    if minimum>0:
        rule(p.get('cgpa') is not None and float(p['cgpa'])>=minimum,'CGPA requirement satisfied.',f'Minimum CGPA is {minimum:g}.')
    lo,hi=o.get('minimum_year') or 1,o.get('maximum_year') or 4
    rule(p.get('current_year') is not None and lo<=p['current_year']<=hi,'Academic year requirement satisfied.',f'Available for academic years {lo} to {hi}.')
    rule(o['listing_status']=='published','Opportunity is published.','This opportunity is not open for applications.',False)
    rule(o['application_deadline']>=now,'Application deadline is open.','Application deadline has passed.',False)
    required=[s for s in skills if s['requirement_type']=='required']
    missing_skills=[s['skill_name'] for s in required if s['skill_id'] not in own_skills]
    required_docs=[d for d in docs if d['is_mandatory']]
    missing_docs=[d['document_name'] for d in required_docs if d['document_type_id'] not in ready_docs]
    components={'Academic eligibility':round(40*sum(academic)/len(academic),1),
        'Required skills':round(30*(1-len(missing_skills)/len(required)),1) if required else 30,
        'Required documents':round(20*(1-len(missing_docs)/len(required_docs)),1) if required_docs else 20,
        'Preparation tasks':round(10*sum(t['task_status']=='completed' for t in tasks)/len(tasks),1) if tasks else 10}
    next_action=next((r['text'] for r in reasons if not r['ok']),None)
    next_action=next_action or (f'Add skill evidence for {missing_skills[0]}.' if missing_skills else None)
    next_action=next_action or (f'Prepare {missing_docs[0]}; save this opportunity to track documents.' if missing_docs else None)
    next_action=next_action or ('Complete linked preparation tasks.' if components['Preparation tasks']<10 else 'Ready to submit an application.')
    return dict(eligible=all(r['ok'] for r in reasons),score=round(sum(components.values())),components=components,
        reasons=reasons,missing_skills=missing_skills,missing_docs=missing_docs,next_action=next_action)


def enrich(profile,opportunities):
    sid=profile['student_id'] if profile else None
    departments=defaultdict(list); skills=defaultdict(list); docs=defaultdict(list)
    for r in query('SELECT od.*,d.department_name FROM opportunity_departments od JOIN departments d ON d.department_id=od.department_id'):
        departments[r['opportunity_id']].append(r)
    for r in query('SELECT os.*,s.skill_name FROM opportunity_skills os JOIN skills s ON s.skill_id=os.skill_id'):
        skills[r['opportunity_id']].append(r)
    for r in query('SELECT od.*,d.document_name FROM opportunity_documents od JOIN document_types d ON d.document_type_id=od.document_type_id'):
        docs[r['opportunity_id']].append(r)
    own={r['skill_id'] for r in query('SELECT skill_id FROM student_skills WHERE student_id=%s',(sid,))} if sid else set()
    apps={r['opportunity_id']:r for r in query('SELECT * FROM applications WHERE student_id=%s',(sid,))} if sid else {}
    ready=defaultdict(set); tasks=defaultdict(list)
    if sid:
        for r in query("SELECT ad.application_id,ad.document_type_id FROM application_documents ad JOIN applications a ON a.application_id=ad.application_id WHERE a.student_id=%s AND ad.document_status IN ('ready','submitted','approved')",(sid,)):
            ready[r['application_id']].add(r['document_type_id'])
        for r in query('SELECT t.* FROM preparation_tasks t JOIN applications a ON a.application_id=t.application_id WHERE a.student_id=%s',(sid,)):
            tasks[r['application_id']].append(r)
    for o in opportunities:
        oid=o['opportunity_id']; a=apps.get(oid); aid=a['application_id'] if a else None
        o.update(departments=departments[oid],skills=skills[oid],documents=docs[oid],application=a)
        o['readiness']=assess(profile,o,[d['department_id'] for d in departments[oid]],skills[oid],docs[oid],own,ready[aid],tasks[aid])
    return opportunities


def references():
    return dict(departments=query('SELECT * FROM departments ORDER BY department_name'),
        categories=query('SELECT * FROM opportunity_categories ORDER BY category_name'),
        skills=query('SELECT * FROM skills ORDER BY skill_name'),
        documents=query('SELECT * FROM document_types ORDER BY document_name'),
        organizations=query('SELECT * FROM organizations ORDER BY organization_name'))
