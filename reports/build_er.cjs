const fs=require('fs');
const path=require('path');
const {instance}=require('C:/Users/Angel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@viz-js/viz/dist/viz.cjs');
const sharp=require('C:/Users/Angel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const meta=JSON.parse(fs.readFileSync(path.join(__dirname,'schema_metadata.json'),'utf8'));
const tables=[...new Set(meta.columns.map(r=>r.TABLE_NAME))];
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function graph(selected,title,full=false){
 let dot='digraph ER { graph [rankdir=LR,bgcolor="white",pad=0.3,nodesep=0.55,ranksep=1.4,splines=spline,label="'+title+'",labelloc=t,fontname="Arial",fontsize=22]; node [shape=plain,fontname="Arial"]; edge [color="#597480",fontname="Arial",fontsize=10,arrowsize=0.5];\n';
 for(const name of selected){
  const cols=meta.columns.filter(r=>r.TABLE_NAME===name);
  dot+='"'+name+'" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" COLOR="#8A9FA8"><TR><TD COLSPAN="2" BGCOLOR="#17394A"><FONT COLOR="white"><B>'+name+'</B></FONT></TD></TR>';
  for(const c of cols){
   const fk=meta.foreign_keys.some(r=>r.TABLE_NAME===name&&r.COLUMN_NAME===c.COLUMN_NAME);
   if(!full && c.COLUMN_KEY!=='PRI'&&!fk&&!['title','application_status','listing_status','full_name','university_uid','department_name','skill_name','document_name','category_name','task_title','email','minimum_cgpa','current_year'].includes(c.COLUMN_NAME)) continue;
   const marker=[c.COLUMN_KEY==='PRI'?'PK':c.COLUMN_KEY==='UNI'?'UQ':'',fk?'FK':''].filter(Boolean).join(' ');
   dot+='<TR><TD ALIGN="LEFT"><FONT COLOR="#126C60">'+marker+'</FONT></TD><TD PORT="'+c.COLUMN_NAME+'" ALIGN="LEFT">'+escape(c.COLUMN_NAME)+'</TD></TR>';
  }
  dot+='</TABLE>>];\n';
 }
 for(const fk of meta.foreign_keys){
  if(!selected.includes(fk.TABLE_NAME)||!selected.includes(fk.REFERENCED_TABLE_NAME)) continue;
  const col=meta.columns.find(r=>r.TABLE_NAME===fk.TABLE_NAME&&r.COLUMN_NAME===fk.COLUMN_NAME);
  const one=(fk.TABLE_NAME==='student_profiles'&&fk.COLUMN_NAME==='user_id')||(fk.TABLE_NAME==='eligibility_requirements'&&fk.COLUMN_NAME==='opportunity_id');
  dot+='"'+fk.REFERENCED_TABLE_NAME+'" -> "'+fk.TABLE_NAME+'" [taillabel="'+(col.IS_NULLABLE==='YES'?'0..1':'1')+'",headlabel="'+(one?'0..1':'0..N')+'",label="'+fk.COLUMN_NAME+'",labeldistance=2,arrowhead=none];\n';
 }
 return dot+'}';
}
(async()=>{
 const viz=await instance();
 const groups={
  er_complete:tables,
  er_students:['users','student_profiles','departments','skills','student_skills','student_interests','opportunity_categories','auth_sessions'],
  er_opportunities:['organizations','opportunity_categories','users','opportunities','eligibility_requirements','departments','opportunity_departments','skills','opportunity_skills','document_types','opportunity_documents'],
  er_applications:['student_profiles','opportunities','applications','application_status_history','users','application_documents','document_types','preparation_tasks','notifications']
 };
 for(const [name,selected] of Object.entries(groups)){
  const dot=graph(selected,name==='er_complete'?'Complete Academic Opportunity Tracker schema':'Academic Opportunity Tracker relationships',name==='er_complete');
  fs.writeFileSync(path.join(__dirname,name+'.dot'),dot);
  const svg=viz.renderString(dot,{format:'svg',engine:'fdp'});
  fs.writeFileSync(path.join(__dirname,name+'.svg'),svg);
  await sharp(Buffer.from(svg),{density:150}).resize({width:name==='er_complete'?6000:3200,withoutEnlargement:false}).png().toFile(path.join(__dirname,name+'.png'));
 }
 console.log('Generated complete and three focused ER diagrams from live PK/FK metadata.');
})().catch(e=>{process.stderr.write(e.message);process.exit(1)});
