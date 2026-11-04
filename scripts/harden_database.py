"""One-time local migration/runtime-user separation; no secret output or data deletion."""
import secrets
from pathlib import Path
from dotenv import dotenv_values,set_key
import mysql.connector

ROOT=Path(__file__).resolve().parents[1]


def main():
    runtime=ROOT/'.env'
    admin_path=ROOT/'.migration.env'
    config=dotenv_values(runtime)
    admin=dotenv_values(admin_path) if admin_path.exists() else config
    if admin.get('DB_NAME')!='campus_opportunity_planner':
        raise SystemExit('Unexpected database name; nothing changed.')
    if not admin_path.exists():
        # Separate privileged setup credentials without changing the root account.
        admin_path.touch(exist_ok=False)
        for key in ('DB_HOST','DB_PORT','DB_USER','DB_PASSWORD','DB_NAME'):
            if key in admin:
                set_key(admin_path,key,admin[key])
    db=mysql.connector.connect(host=admin['DB_HOST'],port=int(admin.get('DB_PORT','3306')),user=admin['DB_USER'],password=admin['DB_PASSWORD'],database=admin['DB_NAME'])
    c=db.cursor()
    try:
        sql='\n'.join(line for line in (ROOT/'database/migrations/001_security.sql').read_text(encoding='utf-8').splitlines() if not line.lstrip().startswith('--'))
        for statement in sql.split(';'):
            if statement.strip():
                c.execute(statement)
        if config.get('DB_USER')=='cu_documents':
            password=config['DB_PASSWORD']
        else:
            password=secrets.token_urlsafe(40)
        c.execute("SELECT COUNT(*) FROM mysql.user WHERE User=%s AND Host=%s",('cu_documents','localhost'))
        exists=c.fetchone()[0]
        if exists and config.get('DB_USER')!='cu_documents':
            raise SystemExit('The chosen runtime account already exists; no existing account password changed. Choose a unique account in this script.')
        if not exists:
            c.execute("CREATE USER %s@%s IDENTIFIED BY %s",('cu_documents','localhost',password))
        permissions={
            'users':'SELECT, INSERT', 'student_profiles':'SELECT, INSERT', 'departments':'SELECT',
            'auth_sessions':'SELECT, INSERT, UPDATE', 'security_rate_limits':'SELECT, INSERT, UPDATE',
        }
        for table,privileges in permissions.items():
            c.execute(f'GRANT {privileges} ON campus_opportunity_planner.{table} TO %s@%s',('cu_documents','localhost'))
        db.commit()
        if config.get('DB_USER')!='cu_documents' or config.get('DB_PASSWORD')!=password:
            # Update in place to preserve restricted Windows ACLs and avoid
            # OneDrive replacement failures. Generated values are URL-safe ASCII.
            lines=runtime.read_text(encoding='utf-8').splitlines()
            lines=[line for line in lines if not line.startswith(('DB_USER=','DB_PASSWORD='))]
            lines.extend(["DB_USER='cu_documents'",f"DB_PASSWORD='{password}'"])
            runtime.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print('Additive migration applied. Flask now uses a restricted non-root account. Existing data and root account retained.')
    except mysql.connector.Error:
        db.rollback()
        raise SystemExit('Migration failed; check private migration credentials. No secrets printed.') from None
    finally:
        c.close()
        db.close()


if __name__=='__main__':
    main()
