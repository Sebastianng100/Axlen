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
    
@app.route('/test_products')
def test_products():
    products = get_products()
    return jsonify(products)  # Return the products as JSON to inspect
    
@app.route('/add_sample_products')
def add_sample_products():
    products = [
        {
            "name": "iPhone 16 Pro Max - Pink",
            "price": 699.99,
            "description": "A high-quality smartphone with excellent features.",
            "image_url": "smartphone.jpg"
        },
        {
            "name": "Macbook - Pink",
            "price": 1299.99,
            "description": "A powerful laptop for work and gaming.",
            "image_url": "laptop.jpg"
        },
        {
            "name": "Airpods Max - Pink",
            "price": 199.99,
            "description": "Noise-canceling headphones for immersive sound.",
            "image_url": "headphones.jpg"
        }
    ]
    products_collection.insert_many(products)
    return "Sample products added!"


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
    # Fetch products with the relevant fields from MongoDB
    products = products_collection.find({}, {"_id": 0, "name": 1, "description": 1, "price": 1, "image_url": 1})
    products_list = list(products)  # Convert the cursor to a list

    print(f"Fetched Products: {products_list}")  # Debug print to verify data
    return products_list

# Flask Route: Add product to the cart (Login Required)
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    username = session['username']  # Get the logged-in user's username
    data = request.get_json()  # Parse JSON data from the AJAX request
    product_name = data.get('product_name')

    product = products_collection.find_one({"name": product_name}, {"_id": 0})
    if not product:
        return jsonify({"status": "error", "message": "Product not found."})

    # Add the product to the user's cart in MongoDB
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
        print(f"Products fetched: {products}")  # Debug print to confirm products

        # Ensure all products contain the 'image_url' key
        for product in products:
            if 'image_url' not in product:
                print(f"Missing 'image_url' for product: {product}")
                product['image_url'] = 'placeholder.jpg'  # Use a default image if missing

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

@app.route('/about')
def about():
    return render_template('about.html')

# Flask Route: Cart Page (Login Required)
@app.route('/cart')
@login_required
def cart():
    username = session['username']
    user = users_collection.find_one({"username": username}, {"_id": 0, "cart": 1})
    cart = user.get("cart", [])
    total = sum(item["price"] for item in cart)

    return render_template('cart.html', cart=cart, total=total)

#Gradio codes
def gradio_interface():
    with gr.Blocks() as demo:
        gr.Markdown("# 🛒 Welcome to Axlen", elem_classes=["text-center", "display-4", "mt-4"])

        # Product listing tab with Add to Cart functionality
        with gr.Tab("Products"):
            gr.Markdown("<h3>Available Products</h3>", elem_classes=["mt-4", "mb-2"])

            # Display products in a DataFrame
            product_display = gr.Dataframe(headers=["Product", "Price", "Description"], interactive=False)
            product_display.value = [[
                item["name"], 
                f"${item['price']:.2f}", 
                item["description"]
            ] for item in get_products()]  # Fetch products from DB and format prices to 2 decimal places

            # Prompt for username and product selection for adding to cart
            user_identifier = gr.Textbox(label="Enter Username", placeholder="Username for Cart Actions")
            selected_product = gr.Dropdown(
                choices=[item["name"] for item in get_products()],
                label="Select a Product to Add to Cart"
            )
            add_to_cart_message = gr.Textbox(label="Cart Status", placeholder="Add items to cart", interactive=False)

            # Add to Cart function and button
            def add_to_cart(username, product_name):
                if not username:
                    return "Please enter your username first."
                response = requests.post(
                    'http://127.0.0.1:5000/add_to_cart', 
                    json={"username": username, "product_name": product_name}
                )
                data = response.json()
                return data.get("message", "Error adding product to cart.")

            gr.Button("Add to Cart").click(
                add_to_cart, 
                inputs=[user_identifier, selected_product], 
                outputs=add_to_cart_message
            )

        # Cart tab to display current cart contents and checkout
        with gr.Tab("Cart"):
            cart_contents = gr.Dataframe(headers=["Product", "Price"], interactive=False, label="Current Cart Contents")
            checkout_status = gr.Textbox(label="Checkout Status", interactive=False)
            total_display = gr.Textbox(label="Total", value="Total: $0.00", interactive=False)

            # Function to view cart contents
            def view_cart(username):
                if not username:
                    return [], "Please enter your username to view cart."
                
                response = requests.get('http://127.0.0.1:5000/get_cart', params={"username": username})
                if response.status_code == 200:
                    data = response.json()
                    cart_items = [[item["name"], f"${item['price']:.2f}"] for item in data.get("cart", [])]
                    total = f"Total: ${data.get('total', 0):.2f}"
                    return cart_items, total
                else:
                    return [], "Error fetching cart."

            gr.Button("Refresh Cart").click(
                view_cart, 
                inputs=user_identifier, 
                outputs=[cart_contents, total_display]
            )

            # Checkout function and button
            def checkout(username):
                if not username:
                    return "Please enter your username to checkout.", ""
                
                response = requests.post('http://127.0.0.1:5000/checkout', json={"username": username})
                if response.status_code == 200:
                    return "Checkout successful! Your cart is now empty.", "Cart is empty."
                else:
                    return "Checkout failed. Please try again.", ""

            gr.Button("Checkout").click(checkout, inputs=user_identifier, outputs=[checkout_status, cart_contents])

    return demo

# Run Flask and Gradio
if __name__ == "__main__":
    from threading import Thread
    def run_flask():
        app.run(port=5000, threaded=False)  # Ensure Flask runs on port 5000

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    interface = gr.Interface(fn=lambda: "Welcome to Axlen", inputs=[], outputs="text")
    interface.launch(share=True)
