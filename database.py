import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv
from flask import g


load_dotenv()


def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=5,
        autocommit=False,
    )
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
