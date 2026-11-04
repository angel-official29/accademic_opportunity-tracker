import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv
from flask import g


load_dotenv()


def get_db_connection():
    connect_kwargs = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "connection_timeout": int(os.getenv("DB_TIMEOUT", "10")),
        "autocommit": False,
    }
    ssl_disabled = os.getenv("DB_SSL_DISABLED", "").strip().lower() in ("true", "1", "yes")
    if ssl_disabled:
        connect_kwargs["ssl_disabled"] = True
    else:
        ssl_ca = os.getenv("DB_SSL_CA", "").strip()
        if ssl_ca and os.path.exists(ssl_ca):
            connect_kwargs["ssl_ca"] = ssl_ca
        if os.getenv("DB_SSL_VERIFY_CERT", "").strip().lower() in ("false", "0", "no"):
            connect_kwargs["ssl_verify_cert"] = False
            connect_kwargs["ssl_verify_identity"] = False

    connection = mysql.connector.connect(**connect_kwargs)
    cursor=connection.cursor()
    try:
        cursor.execute('SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED')
    except Exception:
        connection.close()
        raise
    finally:
        cursor.close()
    return connection


def get_db():
    if 'db' not in g:
        g.db=get_db_connection()
    return g.db


def query(sql,params=(),one=False):
    cursor=get_db().cursor(dictionary=True)
    try:
        cursor.execute(sql,params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()


def execute(sql,params=()):
    cursor=get_db().cursor()
    try:
        cursor.execute(sql,params)
        return cursor.lastrowid
    finally:
        cursor.close()


@contextmanager
def transaction():
    db=get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def close_db(error=None):
    db=g.pop('db',None)
    if db:
        try:
            db.rollback()
        finally:
            db.close()
