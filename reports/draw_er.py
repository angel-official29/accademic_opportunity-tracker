"""Deterministic ER figures using live MySQL metadata and explicit PK/FK links."""
from pathlib import Path
import json,html
from PIL import Image,ImageDraw,ImageFont

OUT=Path(__file__).resolve().parent
meta=json.loads((OUT/'schema_metadata.json').read_text())
cols=meta['columns']; links=meta['foreign_keys']
font_path='C:/Windows/Fonts/calibri.ttf'; bold_path='C:/Windows/Fonts/calibrib.ttf'


def draw(name,positions,full=False):
    cw,rh=610,800 if full else 380
    width=(max(p[0] for p in positions.values())+1)*cw+120
    height=(max(p[1] for p in positions.values())+1)*rh+220
    im=Image.new('RGB',(width,height),'white'); d=ImageDraw.Draw(im)
    f=ImageFont.truetype(font_path,23); b=ImageFont.truetype(bold_path,26); title=ImageFont.truetype(bold_path,36)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>']
    def text(x,y,value,font=f,fill='#17243b',size=23):
        d.text((x,y),value,font=font,fill=fill)
        svg.append(f'<text x="{x}" y="{y+size}" font-family="Calibri,Arial,sans-serif" font-size="{size}" fill="{fill}">{html.escape(value)}</text>')
    def line(points,color='#537581',w=3):
        d.line(points,fill=color,width=w,joint='curve')
        svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{w}"/>')
    def rect(box,fill,outline='#a9b7bc'):
        d.rectangle(box,fill=fill,outline=outline,width=2)
        x,y,x2,y2=box; svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" fill="{fill}" stroke="{outline}"/>')
    text(50,25,'Academic Opportunity Tracker ER diagram',font=title,size=36)
    text(50,80,'PK primary key    FK foreign key    UQ unique    Arrows run from parent to child',size=23)
    selected={}
    for table in positions:
        selected[table]=[r for r in cols if r['TABLE_NAME']==table and (full or r['COLUMN_KEY'] in ('PRI','UNI') or any(l['TABLE_NAME']==table and l['COLUMN_NAME']==r['COLUMN_NAME'] for l in links))]
    boxes={t:(60+x*cw,145+y*rh,60+x*cw+485,145+y*rh+55+34*len(selected[t])) for t,(x,y) in positions.items()}
    for index,fk in enumerate(links):
        parent,child=fk['REFERENCED_TABLE_NAME'],fk['TABLE_NAME']
        if parent not in positions or child not in positions: continue
        pb,cb=boxes[parent],boxes[child]
        row=next(i for i,c in enumerate(selected[child]) if c['COLUMN_NAME']==fk['COLUMN_NAME'])
        cy=cb[1]+66+row*34
        if positions[parent][0]<positions[child][0]:
            start=(pb[2],pb[1]+70); end=(cb[0],cy); middle=(start[0]+end[0])//2
            pts=[start,(middle,start[1]),(middle,end[1]),end]; head=[(end[0]-12,end[1]-7),end,(end[0]-12,end[1]+7)]
        elif positions[parent][0]>positions[child][0]:
            start=(pb[0],pb[1]+70); end=(cb[2],cy); middle=(start[0]+end[0])//2
            pts=[start,(middle,start[1]),(middle,end[1]),end]; head=[(end[0]+12,end[1]-7),end,(end[0]+12,end[1]+7)]
        else:
            start=(pb[2],pb[1]+70); end=(cb[2],cy); middle=pb[2]+45+(index%3)*18
            pts=[start,(middle,start[1]),(middle,end[1]),end]; head=[(end[0]+12,end[1]-7),end,(end[0]+12,end[1]+7)]
        line(pts); line(head)
    for table,box in boxes.items():
        rect(box,'#f7f9fa'); rect((box[0],box[1],box[2],box[1]+48),'#17394a')
        text(box[0]+12,box[1]+8,table,font=b,fill='white',size=26)
        for i,c in enumerate(selected[table]):
            is_fk=any(l['TABLE_NAME']==table and l['COLUMN_NAME']==c['COLUMN_NAME'] for l in links)
            marker=' '.join(v for v in [('PK' if c['COLUMN_KEY']=='PRI' else 'UQ' if c['COLUMN_KEY']=='UNI' else ''),'FK' if is_fk else ''] if v)
            text(box[0]+12,box[1]+58+i*34,marker,fill='#126c60',size=23)
            text(box[0]+117,box[1]+58+i*34,c['COLUMN_NAME'],size=23)
    text(50,height-65,'Cardinality: each parent has 0..N child rows; users to student_profiles and opportunities to eligibility_requirements are 0..1.',size=21)
    text(50,height-35,'Nullable foreign keys allow a child to have no parent. security_rate_limits is an independent HMAC-keyed security table.',size=21)
    svg.append('</svg>'); (OUT/(name+'.svg')).write_text('\n'.join(svg),encoding='utf-8'); im.save(OUT/(name+'.png'))

draw('er_students',{'users':(0,1),'auth_sessions':(0,2),'student_profiles':(1,1),'departments':(1,0),'student_skills':(2,1),'skills':(3,1),'student_interests':(2,2),'opportunity_categories':(3,2)})
draw('er_opportunities',{'users':(0,0),'organizations':(0,1),'opportunity_categories':(0,2),'opportunities':(1,1),'eligibility_requirements':(2,0),'opportunity_departments':(2,1),'departments':(3,1),'opportunity_skills':(2,2),'skills':(3,2),'opportunity_documents':(2,3),'document_types':(3,3)})
draw('er_applications',{'student_profiles':(0,0),'opportunities':(0,1),'applications':(1,1),'application_status_history':(2,0),'users':(3,0),'application_documents':(2,1),'document_types':(3,1),'preparation_tasks':(2,2),'notifications':(3,2)})
all_tables=sorted({r['TABLE_NAME'] for r in cols})
draw('er_complete',{table:(i%5,i//5) for i,table in enumerate(all_tables)},True)
print('Four ER figures generated with explicit PK FK UQ markers and relationship arrows.')
