"""Interactive local administrator creation; stores only a Werkzeug password hash."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from getpass import getpass
from database import get_db_connection
from werkzeug.security import generate_password_hash
from mysql.connector import IntegrityError,Error


def main():
    name=input('Administrator name: ').strip()
    email=input('Administrator email: ').strip().lower()
    password=getpass('Password (10–128 characters): ')
    confirmation=getpass('Confirm password: ')
    if not 2<=len(name)<=100 or not 3<=len(email)<=120 or '@' not in email or password!=confirmation or not 10<=len(password)<=128:
        raise SystemExit('Invalid name/email or password/confirmation.')
    db=get_db_connection()
    c=db.cursor()
    try:
        c.execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'admin')",(name,email,generate_password_hash(password)))
        db.commit()
        print('Administrator created. Sign in using the administrator email.')
    except IntegrityError:
        db.rollback()
        raise SystemExit('That email already exists; no existing account changed.') from None
    finally:
        c.close()
        db.close()


if __name__=='__main__':
    try:
        main()
    except Error:
        raise SystemExit('Database operation failed. Check private local configuration.') from None
