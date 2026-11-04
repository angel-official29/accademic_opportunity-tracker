"""Authorized localhost-only smoke checks. Uses disposable fixture identity, no secrets output."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import secrets
import re
import urllib.request
import urllib.parse
import urllib.error
from http.cookiejar import CookieJar
from dotenv import dotenv_values
import mysql.connector
from werkzeug.security import generate_password_hash

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:5000'


def main():
    e=dotenv_values(ROOT/'.migration.env')
    db=mysql.connector.connect(host=e['DB_HOST'],port=int(e.get('DB_PORT','3306')),user=e['DB_USER'],password=e['DB_PASSWORD'],database=e['DB_NAME'])
    c=db.cursor()
    password=secrets.token_urlsafe(20)
    uid='26bit'+str(secrets.randbelow(900000)+100000)
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    user_id=None
    def get(path):
        return opener.open(BASE+path,timeout=10)
    def post(path,data):
        return opener.open(BASE+path,urllib.parse.urlencode(data).encode(),timeout=10)
    def token(path='/login'):
        with get(path) as response:
            return re.search(r'name="csrf_token" value="([^"]+)"',response.read().decode('utf-8')).group(1)
    try:
        c.execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'student')",('Live audit fixture',uid+'@cuchd.in',generate_password_hash(password)))
        user_id=c.lastrowid
        db.commit()
        with get('/') as r:
            assert r.status==200 and r.headers.get('Permissions-Policy')
        print('PASS homepage + security headers')
        for path in ('/login','/register'):
            with get(path) as r:
                assert r.status==200
            print('PASS '+path)
        with get('/profile/setup') as r:
            assert r.geturl().endswith('/login')
        print('PASS protected profile redirects when logged out')
        try:
            post('/login',{'identifier':uid,'password':password})
            raise AssertionError('CSRF-free login was accepted')
        except urllib.error.HTTPError as error:
            assert error.code==400
        print('PASS CSRF-free login rejected')
        with post('/login',{'identifier':uid,'password':password,'csrf_token':token()}) as r:
            assert r.status==200
        with get('/profile/setup') as r:
            assert r.status==200 and b'Academic Details' in r.read()
        print('PASS UID login + academic profile')
        try:
            get('/database-test')
            raise AssertionError('Student accessed database diagnostic')
        except urllib.error.HTTPError as error:
            assert error.code==403
        print('PASS diagnostic denied to student')
        with post('/logout',{'csrf_token':token('/profile/setup')}) as r:
            assert r.status==200
        with get('/profile/setup') as r:
            assert r.geturl().endswith('/login')
        print('PASS POST logout + protected-route rejection')
    finally:
        if user_id:
            c.execute('UPDATE users SET is_active=FALSE WHERE user_id=%s',(user_id,))
            db.commit()
        c.close()
        db.close()


if __name__=='__main__':
    main()
