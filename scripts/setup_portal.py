"""Add the review status and minimal portal grants; preserve all existing records."""
from pathlib import Path
from dotenv import dotenv_values
import mysql.connector

ROOT=Path(__file__).resolve().parents[1]


def main():
    a=dotenv_values(ROOT/'.migration.env'); runtime=dotenv_values(ROOT/'.env')
    if a['DB_NAME']!='campus_opportunity_planner' or runtime['DB_USER']!='cu_documents': raise SystemExit('Unexpected local configuration; no changes made.')
    db=mysql.connector.connect(host=a['DB_HOST'],port=int(a.get('DB_PORT','3306')),user=a['DB_USER'],password=a['DB_PASSWORD'],database=a['DB_NAME'])
    c=db.cursor()
    try:
        c.execute("SELECT COLUMN_TYPE FROM information_schema.columns WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='applications' AND COLUMN_NAME='application_status'")
        if "'under_review'" not in c.fetchone()[0]:
            sql='\n'.join(line for line in (ROOT/'database/migrations/002_portal.sql').read_text().splitlines() if not line.lstrip().startswith('--'))
            for statement in sql.split(';'):
                if statement.strip(): c.execute(statement)
        rights={'users':'SELECT, INSERT','student_profiles':'SELECT, INSERT, UPDATE','departments':'SELECT',
            'skills':'SELECT','student_skills':'SELECT, INSERT, DELETE','organizations':'SELECT','opportunity_categories':'SELECT',
            'opportunities':'SELECT, INSERT, UPDATE','eligibility_requirements':'SELECT, INSERT, UPDATE',
            'opportunity_departments':'SELECT, INSERT, DELETE','opportunity_skills':'SELECT, INSERT, DELETE','opportunity_documents':'SELECT, INSERT, DELETE',
            'applications':'SELECT, INSERT, UPDATE','application_status_history':'SELECT, INSERT','document_types':'SELECT',
            'application_documents':'SELECT, INSERT, UPDATE','preparation_tasks':'SELECT, INSERT, UPDATE','student_interests':'SELECT',
            'notifications':'SELECT, INSERT','auth_sessions':'SELECT, INSERT, UPDATE','security_rate_limits':'SELECT, INSERT, UPDATE'}
        for table,permissions in rights.items():
            c.execute(f'GRANT {permissions} ON campus_opportunity_planner.{table} TO %s@%s',('cu_documents','localhost'))
        db.commit(); print('Portal migration and restricted table-level grants applied. Existing data retained.')
    finally: c.close(); db.close()


if __name__=='__main__': main()
