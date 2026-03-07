import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# ------------------ Initialize App ------------------

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'student_project_secret_123')

# ------------------ Database Setup ------------------

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------ Database Models ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Order(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    items = db.Column(db.Text, nullable=False)
    total = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Create tables
with app.app_context():
    db.create_all()

# ------------------ Product Data ------------------

products = {
    'non_veg_pickles': [
        {'id': 1, 'name': 'Chicken Pickle', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
        {'id': 2, 'name': 'Fish Pickle', 'weights': {'250': 200, '500': 400, '1000': 800}},
        {'id': 3, 'name': 'Gongura Mutton', 'weights': {'250': 400, '500': 800, '1000': 1600}},
        {'id': 4, 'name': 'Mutton Pickle', 'weights': {'250': 400, '500': 800, '1000': 1600}},
        {'id': 5, 'name': 'Gongura Prawns', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
        {'id': 6, 'name': 'Chicken Pickle (Gongura)', 'weights': {'250': 350, '500': 700, '1000': 1050}}
    ],

    'veg_pickles': [
        {'id': 7, 'name': 'Traditional Mango Pickle', 'weights': {'250': 150, '500': 280, '1000': 500}},
        {'id': 8, 'name': 'Zesty Lemon Pickle', 'weights': {'250': 120, '500': 220, '1000': 400}},
        {'id': 9, 'name': 'Tomato Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
        {'id': 10, 'name': 'Kakarakaya Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
        {'id': 11, 'name': 'Chintakaya Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
        {'id': 12, 'name': 'Spicy Pandu Mirchi', 'weights': {'250': 130, '500': 240, '1000': 450}}
    ],

    'snacks': [
        {'id': 13, 'name': 'Banana Chips', 'weights': {'250': 300, '500': 600, '1000': 800}},
        {'id': 14, 'name': 'Ragi Laddu', 'weights': {'250': 350, '500': 700, '1000': 1000}},
        {'id': 15, 'name': 'Dry Fruit Laddu', 'weights': {'250': 500, '500': 1000, '1000': 1500}}
    ]
}

# ------------------ Routes ------------------

@app.route('/')
def index():
    return render_template('index.html')


# ------------------ Signup ------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            return render_template('signup.html', error="Username already exists")

        if User.query.filter_by(email=email).first():
            return render_template('signup.html', error="Email already registered")

        hashed_pw = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully!")
        return redirect(url_for('login'))

    return render_template('signup.html')


# ------------------ Login ------------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session['logged_in'] = True
            session['username'] = username

            return redirect(url_for('home'))

        return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


# ------------------ Logout ------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ------------------ Home ------------------

@app.route('/home')
def home():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template('home.html')


# ------------------ Product Category ------------------

@app.route('/category/<type>')
def show_products(type):

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if type in products:
        return render_template(f"{type}.html", products=products[type])

    return redirect(url_for('home'))


# ------------------ Checkout ------------------

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':

        cart_json = request.form.get('cart_data', '[]')
        total = float(request.form.get('total_amount', '0'))

        new_order = Order(
            id=str(uuid.uuid4()),
            username=session['username'],
            items=cart_json,
            total=total
        )

        db.session.add(new_order)
        db.session.commit()

        flash("Order placed successfully!")
        return redirect(url_for('home'))

    return render_template('checkout.html')


# ------------------ Homemade Status Route ------------------

@app.route('/homemade')
def homemade():
    return jsonify({"status": "Homemade Pickle Store Application Running"}), 200


# ------------------ Run App ------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
