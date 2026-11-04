import os
import math
import secrets
from datetime import datetime
from flask import g
from mysql.connector import IntegrityError

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import query,execute,transaction
from security import configure,identity,UID,role_required,begin_session,revoke_session


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
configure(app)
DUMMY_HASH=generate_password_hash(secrets.token_urlsafe(24))


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/")
def home():
    if g.user:
        return redirect(url_for('admin.dashboard' if g.user['role']=='admin' else 'student.dashboard'))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for('home'))
    if request.method == 'POST':
        try:
            uid,email=identity(request.form.get('university_uid',''),request.form.get('email',''))
            full_name=request.form.get('full_name','').strip()
            password=request.form.get('password','')
            if not 2<=len(full_name)<=100:
                raise ValueError('Full name must contain 2–100 characters.')
            if not 10<=len(password)<=128:
                raise ValueError('Use a password with 10–128 characters.')
            if password!=request.form.get('confirm_password'):
                raise ValueError('Passwords do not match.')
            with transaction():
                if query('SELECT student_id FROM student_profiles WHERE LOWER(university_uid)=%s',(uid,),one=True):
                    raise ValueError('That UID or university email is already registered.')
                execute("INSERT INTO users (full_name,email,password_hash,role) VALUES (%s,%s,%s,'student')",(full_name,email,generate_password_hash(password)))
            flash('Account created successfully. Please sign in.','success')
            return redirect(url_for('login'))
        except ValueError as error:
            flash(str(error),'error')
        except IntegrityError:
            flash('That UID or university email is already registered.','error')
    return render_template('register.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for('home'))
    if request.method == 'POST':
        identifier=request.form.get('identifier',request.form.get('email','')).strip().lower()
        password=request.form.get('password','')
        user=None
        if len(identifier)<=120 and 1<=len(password)<=128:
            if '@' in identifier:
                user=query('SELECT user_id,password_hash,is_active,role FROM users WHERE LOWER(email)=%s',(identifier,),one=True)
            elif UID.fullmatch(identifier):
                user=query("""SELECT u.user_id,u.password_hash,u.is_active,u.role FROM users u LEFT JOIN student_profiles p ON p.user_id=u.user_id
                    WHERE u.role='student' AND (LOWER(p.university_uid)=%s OR (p.student_id IS NULL AND LOWER(u.email)=%s))""",(identifier,identifier+'@cuchd.in'),one=True)
            valid=check_password_hash(user['password_hash'] if user else DUMMY_HASH,password)
            if user and valid and user['is_active']:
                begin_session(user['user_id'])
                flash('Welcome back!','success')
                return redirect(url_for('admin.dashboard' if user['role']=='admin' else 'student.dashboard'))
        flash('Invalid email or password.','error')
    return render_template('login.html')

@app.route("/profile/setup", methods=["GET", "POST"])
@role_required('student')
def profile_setup():
    existing=query('SELECT student_id FROM student_profiles WHERE user_id=%s',(g.user['user_id'],),one=True)
    if existing:
        flash('Your academic profile is already complete.','success')
        return redirect(url_for('home'))
    if request.method == 'POST':
        try:
            uid,_=identity(request.form.get('university_uid',''),g.user['email'])
            department=int(request.form.get('department_id','0'))
            year=int(request.form.get('current_year','0'))
            cgpa=float(request.form['cgpa']) if request.form.get('cgpa') else None
            graduation=int(request.form['graduation_year']) if request.form.get('graduation_year') else None
            if not 1<=year<=4 or (cgpa is not None and (not math.isfinite(cgpa) or not 0<=cgpa<=10)):
                raise ValueError('Choose year 1–4 and a CGPA between 0 and 10.')
            if graduation is not None and not datetime.now().year<=graduation<=datetime.now().year+10:
                raise ValueError('Choose a graduation year within the next ten years.')
            if not query('SELECT department_id FROM departments WHERE department_id=%s',(department,),one=True):
                raise ValueError('Choose an available department.')
            with transaction():
                # UNIQUE(user_id) safely arbitrates concurrent inserts; duplicates roll back below.
                if not query('SELECT student_id FROM student_profiles WHERE user_id=%s',(g.user['user_id'],),one=True):
                    execute('INSERT INTO student_profiles (user_id,university_uid,department_id,current_year,cgpa,graduation_year) VALUES (%s,%s,%s,%s,%s,%s)',(g.user['user_id'],uid,department,year,cgpa,graduation))
            flash('Academic profile completed successfully.','success')
            return redirect(url_for('home'))
        except ValueError as error:
            message=str(error)
            flash('Enter valid numeric academic details.' if message.startswith(('invalid literal','could not convert')) else message,'error')
        except IntegrityError:
            flash('That UID or profile already exists.','error')
    departments=query('SELECT department_id,department_name FROM departments ORDER BY department_name')
    return render_template('profile_setup.html',departments=departments)
@app.post("/logout")
def logout():
    revoke_session()
    flash('You have been logged out.','success')
    return redirect(url_for('home'))


@app.route("/database-test")
@role_required('admin')
def database_test():
    query('SELECT 1 AS available',one=True)
    return 'Database connection available.' 


from student_portal import bp as student_blueprint
from admin_portal import bp as admin_blueprint
app.register_blueprint(student_blueprint)
app.register_blueprint(admin_blueprint)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_debugger=False, use_reloader=False)
