"""Read-only verification. Reports locations/counts/booleans, never secret values."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from database import get_db_connection

ROOT=Path(__file__).resolve().parents[1]


def main():
    config=dotenv_values(ROOT/'.env')
    migration=dotenv_values(ROOT/'.migration.env')
    demo=dotenv_values(ROOT/'.report-demo.env')
    secrets={f'{index}:{key}':value for index,source in enumerate((config,migration,demo)) for key,value in source.items() if value and ('PASSWORD' in key or 'SECRET' in key)}
    hits=[]
    count=0
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in ('.venv','__pycache__','.git','.audit-venv') for part in path.parts):
            continue
        if path.name in ('.env','.migration.env','.report-demo.env') or path.suffix not in ('.py','.html','.sql','.js','.css','.md','.log','.txt'):
            continue
        count+=1
        text=path.read_text(encoding='utf-8',errors='replace')
        for key,value in secrets.items():
            if value in text:
                hits.append((str(path.relative_to(ROOT)),key))
    print('Configured-secret scan:', 'PASS' if not hits else 'FAIL',f'({count} text files)')
    if hits:
        print('Locations and key names only:',hits)
        raise SystemExit('Potential secret exposure; rotate affected values. Values omitted.')
    print('Git history:', 'present; separate scan required' if (ROOT/'.git').exists() else 'not present / not assessed')
    db=get_db_connection()
    c=db.cursor()
    try:
        c.execute('SELECT CURRENT_USER(),@@transaction_isolation')
        principal,isolation=c.fetchone()
        assert not principal.startswith('root@')
        assert isolation=='READ-COMMITTED'
        c.execute('SHOW GRANTS')
        grants=[r[0] for r in c.fetchall()]
        assert not any('ALL PRIVILEGES' in value or 'DROP' in value or 'ALTER' in value or 'GRANT OPTION' in value for value in grants)
        print('Restricted runtime principal and transaction isolation: PASS')
    finally:
        c.close()
        db.close()


if __name__=='__main__':
    main()
