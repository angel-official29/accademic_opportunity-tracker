"""HTTP verification of portal pages with fictional demo accounts, no screenshot workaround."""
import re,json
from pathlib import Path
from urllib.request import build_opener,HTTPCookieProcessor
from urllib.parse import urlencode
from http.cookiejar import CookieJar
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:5000'


def main():
    e=dotenv_values(ROOT/'.report-demo.env'); results=[]
    for role,email,password in [('student',e['STUDENT_EMAIL'],e['STUDENT_PASSWORD']),('admin',e['ADMIN_EMAIL'],e['ADMIN_PASSWORD'])]:
        opener=build_opener(HTTPCookieProcessor(CookieJar()))
        with opener.open(BASE+'/login',timeout=10) as response:
            text=response.read().decode('utf-8')
        token=re.search(r'name="csrf_token" value="([^"]+)"',text).group(1)
        with opener.open(BASE+'/login',urlencode({'identifier':email,'password':password,'csrf_token':token}).encode(),timeout=10) as response:
            assert response.geturl().endswith('/'+role+'/dashboard')
        paths=['/student/dashboard','/student/discover','/student/profile','/student/applications',f'/student/opportunities/{e["OPPORTUNITY_ID"]}',f'/student/applications/{e["APPLICATION_ID"]}'] if role=='student' else ['/admin/dashboard','/admin/opportunities','/admin/opportunities/new',f'/admin/opportunities/{e["OPPORTUNITY_ID"]}/edit','/admin/applications',f'/admin/applications/{e["APPLICATION_ID"]}']
        if role=='admin':
            tables=json.loads((ROOT/'reports/schema_metadata.json').read_text())['columns']
            paths+=['/admin/database?table='+name for name in sorted({r['TABLE_NAME'] for r in tables})]
        for path in paths:
            with opener.open(BASE+path,timeout=10) as response:
                assert response.status==200
                assert response.headers.get('Content-Security-Policy')
                results.append({'role':role,'path':path,'status':response.status})
        print(f'PASS {role}: {len(paths)} live portal/schema routes')
    (ROOT/'security-audit/portal-http-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('Total successful live authenticated GET checks:',len(results))


if __name__=='__main__': main()
