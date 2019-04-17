from flask import Flask, render_template, make_response, flash, redirect, url_for, session, request, logging
import random
from flask_mysqldb import MySQL
from flask_wtf import Form
from wtforms import DateField, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import pdfkit
from twilio.rest import Client
from datetime import date
import os


app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'laser123'
app.config['MYSQL_DB'] = 'company_review'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

#Articles = Articles()

# Index
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/reviews')
def reviews():

    cur=mysql.connection.cursor()

    result=cur.execute("SELECT * FROM reviews ORDER BY r_upvotes DESC")

    reviews = cur.fetchall()

    if result > 0:
        return render_template('reviews.html', reviews=reviews)
    else:
        msg = 'No facilites available currently'
        return render_template('reviews.html', msg=msg)

    cur.close()

@app.route('/companies')
def companies():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM companies ORDER BY c_size DESC")

    companies = cur.fetchall()

    if result > 0:
        return render_template('companies.html', companies=companies)
    else:
        msg = 'No Companies available in the Database currently'
        return render_template('companies.html', msg=msg)

@app.route('/view_review/<string:id>/')
def view_review(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM reviews WHERE r_id = %s", [id])

    review = cur.fetchone()

    return render_template('view_review.html', review=review)

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=6, max=150),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    print("YAYAYA")
    if form.username.data != '':
        print("hereeee")
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])


        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            print(data['username'])
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(request.form['password'], password):
                print("matched and redirecting....")
                # Passed
                #app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['username']  = username

                flash('Successfully logged in!', 'success')

                return redirect(url_for('dashboard'))

            else:
                print("wrong password")
                error = 'Invalid login'
                app.logger.info('PASSWORD DOES NOT MATCH')
                return render_template('login.html', error=error)

            cur.close()
            
        else:
            error = 'Username not found'
            app.logger.info('NO SUCH USER')
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)

    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return (f(*args, **kwargs))
        else:
            flash('Unauthorised access!', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('reviews'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')

@app.route('/user_reviews')
@is_logged_in
def user_reviews():
    cur = mysql.connection.cursor()

    user = session['username']

    result = cur.execute("SELECT * FROM reviews WHERE r_user=%s ORDER BY r_upvotes DESC", [user])

    reviews = cur.fetchall()

    # if result > 0:
        
    # else:
    #     msg = 'No Reviews have been added by you!'
    #     return render_template('user_reviews.html', msg=msg)

    cur.close()
    return render_template('user_reviews.html', reviews=reviews)

@app.route('/user_reviewsG')
@is_logged_in
def user_reviewsG():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM reviews ORDER BY r_upvotes DESC")

    reviews = cur.fetchall()

    if result > 0:
        return render_template('user_reviewsG.html', reviews=reviews)
    else:
        msg = 'No Reviews available'
        return render_template('dashboard.html', msg=msg)

    cur.close()
    return render_template('user_reviewsG.html')

class ReviewForm(Form):
    id = StringField('ID')
    upvotes = StringField('Upvotes')
    company = StringField('Company')
    title = StringField('Title', [validators.Length(min=2, max=200)])
    description = TextAreaField('Description', [validators.Length(min=30)])


@app.route('/add_review', methods=['GET', 'POST'])
@is_logged_in
def add_review():
    form = ReviewForm()

    if form.validate_on_submit():
        print("YES")
        idd = form.id.data
        print(idd)
        upvotes = 0
        company = form.company.data
        title = form.title.data
        description = form.description.data

        print(session['username'])

        user = session['username']

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO reviews(r_id, r_upvotes, r_company, r_title, r_description, r_user) VALUES(%s, %s, %s, %s, %s, %s)", (idd, upvotes, company, title, description, user))

        mysql.connection.commit()

        cur.close()

        flash('Review Added Successfully', 'success')

        return redirect(url_for('user_reviews'))
    print(form.errors)
    return render_template('add_review.html', form=form)

@app.route('/edit_review/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_review(id):
    print("&&&&&FFGTHTRH")
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM reviews WHERE r_id=%s", [id])

    review = cur.fetchone()

    form = ReviewForm()

    form.title.data = str(review['r_title'])
    form.description.data  = review['r_description']
    form.company.data = review['r_company']
    form.upvotes.data = review['r_upvotes']
    form.id.data      = review['r_id']

    if form.validate_on_submit():
        title = request.form['title']
        description  = request.form['description']

        cur = mysql.connection.cursor()

        cur.execute("UPDATE reviews SET r_title=%s, r_description=%s WHERE r_id=%s", (title, description, id))

        mysql.connection.commit()

        cur.close()

        flash('Review Updated successfully', 'success')

        return redirect(url_for('dashboard'))

    print(form.errors)
    return render_template('edit_review.html', form=form)

@app.route('/delete_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_amenity(id):
    cur=mysql.connection.cursor()

    cur.execute("DELETE FROM reviews WHERE a_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Facility Deleted', 'success')

    return redirect(url_for('admin_amenities'))

@app.route('/user_companies')
@is_logged_in
def user_companies():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM companies")

    companies = cur.fetchall()

    if result > 0:
        return render_template('user_companies.html', companies=companies)
    else:
        flash('No Companies available in the Database!', 'danger')
        redirect(url_for('add_company'))

    cur.close()
    return render_template('user_companies.html')

class CompanyForm(Form):
    id = StringField('ID', [validators.Length(min=3, max=5)])
    name = StringField('Company Name', [validators.Length(min=1, max=3)])
    size = StringField('Number of Employees')
    location = StringField('Location')
    revenue = StringField('Revenue')


@app.route('/add_company', methods=['GET', 'POST'])
@is_logged_in
def add_company():
    form = CompanyForm()

    if request.method == 'POST':
        id = form.id.data
        name = form.name.data
        size = form.size.data
        location = form.location.data
        revenue = form.revenue.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO companies(c_id, c_name, c_size, c_location, c_revenue) VALUES(%s, %s, %s, %s, %s)", (id, name, size, location, revenue))

        mysql.connection.commit()

        cur.close()

        flash('Company added successfully!', 'success')

        return redirect(url_for('user_companies'))

    return render_template('add_company.html', form=form)

@app.route('/edit_company/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_company(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM companies WHERE c_id=%s", [id])

    company = cur.fetchone()

    form = CompanyForm()

    form.name.data = company['c_name']
    form.size.data = company['c_size']
    form.location.data = company['c_location']
    form.revenue.data = company['c_revenue']

    if request.method == 'POST':
        print("INSIDE")
        size = request.form['size']
        location = request.form['location']
        revenue = request.form['revenue']

        cur = mysql.connection.cursor()

        cur.execute("UPDATE companies SET c_size=%s, c_location=%s, c_revenue=%s WHERE c_id=%s", (size, location, revenue, id))

        mysql.connection.commit()

        cur.close()

        flash('Company details updated successfully', 'success')

        return redirect(url_for('user_companies'))

    return render_template('edit_company.html', form=form, id=id)

@app.route('/delete_company/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_company(id):
    cur=mysql.connection.cursor()

    cur.execute("DELETE FROM companies WHERE c_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Company details deleted', 'success')

    return redirect(url_for('user_companies'))

class DateForm(Form):
    dt = DateField('Pick a Date', format="%m/%d/%Y")


@app.route('/date', methods=['post','get'])
def home():
    form = DateForm()
    if form.validate_on_submit():
        print(form.dt.data)
        return form.dt.data.strftime('%Y-%m-%d')
    return render_template('example.html', form=form)

@app.route('/upvote/<string:id>', methods=['GET', 'POST'])
def upvote_review(id):

    cur = mysql.connection.cursor()

    user = session['username']

    result = cur.execute("SELECT * FROM reviews WHERE r_id=%s", [id])
    print(result)
    ans = cur.fetchone()

    if ans['r_user'] == user :

        flash('You cannot upvote your own review!', 'danger')
        cur.close()

        return redirect(url_for('user_reviewsG'))

    cur.execute("UPDATE reviews SET r_upvotes = r_upvotes+1 WHERE r_id = %s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Review Upvoted successfully', 'success')

    return redirect(url_for('user_reviewsG'))


if __name__ == '__main__':
    SECRET_KEY = os.urandom(32)
    app.config['SECRET_KEY'] = SECRET_KEY

    print(SECRET_KEY)

    SECRET_KEY = os.urandom(32)
    app.config['WTF_CSRF_SECRET_KEY']=SECRET_KEY

    app.run(debug = True)
