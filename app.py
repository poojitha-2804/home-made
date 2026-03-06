import os
import json
import uuid
import boto3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from decimal import Decimal

# 1. Initialize App & Config
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_very_secret_key_12345')

# 2. AWS DynamoDB Setup
# Ensure your AWS credentials are set in environment variables or ~/.aws/credentials
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
users_table = dynamodb.Table('Users')
orders_table = dynamodb.Table('Orders')

# 3. Product Data Store
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

# ================== AUTH ROUTES ==================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        try:
            # Check if user exists
            response = users_table.get_item(Key={'username': username})
            if 'Item' in response:
                return render_template('signup.html', error='Username already taken')

            # Hash and Store
            hashed_pw = generate_password_hash(password)
            users_table.put_item(
                Item={'username': username, 'email': email, 'password': hashed_pw}
            )
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Signup Error: {e}")
            return render_template('signup.html', error='Database error')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            response = users_table.get_item(Key={'username': username})
            if 'Item' in response:
                user = response['Item']
                if check_password_hash(user['password'], password):
                    session['logged_in'] = True
                    session['username'] = username
                    return redirect(url_for('home'))
            
            return render_template('login.html', error='Invalid credentials')
        except Exception as e:
            return render_template('login.html', error='Login failed')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================== SHOP ROUTES ==================

@app.route('/home')
def home():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/category/<type>')
def show_products(type):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if type in products:
        return render_template(f'{type}.html', products=products[type])
    return redirect(url_for('home'))

# ================== CHECKOUT LOGIC ==================

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        
        # Parse Cart Data from JSON hidden input
        try:
            cart_json = request.form.get('cart_data', '[]')
            cart_items = json.loads(cart_json, parse_float=Decimal)
            total = Decimal(request.form.get('total_amount', '0'))

            if not cart_items:
                return render_template('checkout.html', error="Cart is empty")

            order_id = str(uuid.uuid4())
            orders_table.put_item(
                Item={
