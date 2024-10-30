#app.config['MONGO_URI'] = "mongodb+srv://sngofficial100:T0218191b@technest.wlno2.mongodb.net/shopping?retryWrites=true&w=majority&appName=TechNest"

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_pymongo import PyMongo
from flask_session import Session
import random  # For generating verification codes
from werkzeug.security import generate_password_hash, check_password_hash
import gradio as gr
import requests
from functools import wraps
from bson.objectid import ObjectId  # Ensure this import is at the top

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for Flask sessions
app.config['MONGO_URI'] = "mongodb+srv://sngofficial100:T0218191b@technest.wlno2.mongodb.net/shopping?retryWrites=true&w=majority&appName=TechNest"
app.config['SESSION_TYPE'] = 'filesystem'  # Use the filesystem to store sessions
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 1 day in seconds
Session(app)  # Initialize the session
mongo = PyMongo(app)

# MongoDB Collections
users_collection = mongo.db.users
products_collection = mongo.db.products

@app.route('/test_mongo')
def test_mongo():
    try:
        # Insert a dummy product into MongoDB for testing
        products_collection.insert_one({"name": "Test Product", "price": 0})
        return "MongoDB connection is successful!"
    except Exception as e:
        return f"Error connecting to MongoDB: {str(e)}"

@app.route('/test_insert')
def test_insert():
    try:
        users_collection.insert_one({"username": "testuser", "email": "test@test.com", "verified": False})
        return "Test insert successful!"
    except Exception as e:
        return f"MongoDB Insert Error: {str(e)}"

# Helper: Check if User is Logged In
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))  # Redirect to login if not logged in
        return f(*args, **kwargs)
    return decorated_function

# Helper function to fetch all products
def get_products():
    return list(products_collection.find({}, {"_id": 0}))

# Flask Route: Add product to the cart (Login Required)
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    username = session['username']  # Get logged-in user
    product_name = request.json.get('product_name')

    product = products_collection.find_one({"name": product_name}, {"_id": 0})
    if not product:
        return jsonify({"status": "error", "message": "Product not found."})

    # Add product to the user's cart in MongoDB
    users_collection.update_one(
        {"username": username},
        {"$push": {"cart": product}}
    )

    return jsonify({"status": "success", "message": f"{product_name} added to cart."})

# Flask Route: Get cart contents
@app.route('/get_cart', methods=['GET'])
def get_cart():
    username = request.args.get('username')  # Identify user
    user = users_collection.find_one({"username": username}, {"_id": 0, "cart": 1})
    if not user or "cart" not in user:
        return jsonify({"cart": [], "total": 0})

    cart = user["cart"]
    total = sum(item["price"] for item in cart)

    return jsonify({"cart": cart, "total": total})

# Flask Route: Checkout (Login Required)
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    username = session['username']
    users_collection.update_one({"username": username}, {"$set": {"cart": []}})
    flash("Checkout successful! Thank you for your purchase.")
    return redirect(url_for('home'))

# Route: Display Products on Homepage
@app.route('/')
def home():
    try:
        products = get_products()
        print(f"Products fetched: {products}")  # Debug print
        return render_template('index.html', products=products)
    except Exception as e:
        print(f"Error in home route: {e}")  # Print the error to the console
        return "Internal Server Error", 500

# Flask Route: User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier').strip()
        password = request.form.get('password').strip()

        if not identifier or not password:
            flash("Both fields are required.", "danger")
            return redirect(url_for('login'))

        user = users_collection.find_one({
            "$or": [{"username": identifier}, {"email": identifier}]
        })

        if user and check_password_hash(user["password"], password):
            session['username'] = user["username"]
            session['email'] = user["email"]
            flash("Login successful!", "success")
            return redirect(url_for('home'))

        flash("Invalid credentials. Please try again.", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')

# Flask Route: User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username').strip()
            email = request.form.get('email').strip()
            password = request.form.get('password').strip()

            print(f"Received data - Username: {username}, Email: {email}, Password: {password}")

            if not username or not email or not password:
                flash("All fields are required.", "danger")
                return redirect(url_for('register'))

            existing_user = users_collection.find_one({
                "$or": [{"username": username}, {"email": email}]
            })

            if existing_user:
                flash("Username or Email already exists. Please use a different one.", "warning")
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)
            new_user = {
                "username": username,
                "email": email,
                "password": hashed_password,
                "verified": False,
                "cart": []
            }

            result = users_collection.insert_one(new_user)
            print(f"User inserted successfully with ID: {result.inserted_id}")

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Error during registration: {e}")
            flash("An unexpected error occurred. Please try again.", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

# Flask Route: Logout
@app.route('/logout')
def logout():
    print(f"Logging out user: {session.get('username')}")  # Debug print
    session.pop('username', None)
    flash("Logged out successfully.")
    return redirect(url_for('home'))

# Flask Route: Cart Page (Login Required)
@app.route('/cart')
@login_required
def cart():
    username = session['username']
    user = users_collection.find_one({"username": username}, {"_id": 0, "cart": 1})
    cart = user.get("cart", [])
    total = sum(item["price"] for item in cart)

    return render_template('cart.html', cart=cart, total=total)

# Run Flask and Gradio
if __name__ == "__main__":
    from threading import Thread
    def run_flask():
        app.run(port=5000, threaded=False)  # Ensure Flask runs on port 5000

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    interface = gr.Interface(fn=lambda: "Welcome to Axlen", inputs=[], outputs="text")
    interface.launch(share=True)
