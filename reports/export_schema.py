"""Export schema metadata only, never record values or credentials."""
from pathlib import Path
import json
from dotenv import dotenv_values
import mysql.connector

ROOT=Path(__file__).resolve().parents[1]
e=dotenv_values(ROOT/'.migration.env')
db=mysql.connector.connect(host=e['DB_HOST'],port=int(e.get('DB_PORT','3306')),user=e['DB_USER'],password=e['DB_PASSWORD'],database=e['DB_NAME'])
c=db.cursor(dictionary=True)
try:
    c.execute('SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,COLUMN_KEY,IS_NULLABLE FROM information_schema.columns WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION')
    columns=c.fetchall()
    c.execute('SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME FROM information_schema.key_column_usage WHERE TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL ORDER BY TABLE_NAME,COLUMN_NAME')
    links=c.fetchall()
    out=ROOT/'reports/schema_metadata.json'
    out.write_text(json.dumps({'columns':columns,'foreign_keys':links},indent=2),encoding='utf-8')
    print('Exported metadata for',len({r['TABLE_NAME'] for r in columns}),'MySQL tables; no row data.')
finally: c.close(); db.close()
