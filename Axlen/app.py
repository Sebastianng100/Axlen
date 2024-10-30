#app.config['MONGO_URI'] = "mongodb+srv://sngofficial100:T0218191b@technest.wlno2.mongodb.net/shopping?retryWrites=true&w=majority&appName=TechNest"

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_pymongo import PyMongo
from flask_session import Session
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
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
Session(app)  # Initialize the session
mongo = PyMongo(app)

# MongoDB Collections
users_collection = mongo.db.users
products_collection = mongo.db.products

@app.route('/test_mongo')
def test_mongo():
    try:
        product = products_collection.find_one()
        if product:
            # Convert the ObjectId to a string
            product['_id'] = str(product['_id'])
        print(f"Test Mongo Product: {product}")  # Debug print
        return jsonify({"status": "success", "product": product}), 200
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")  # Debugging
        return "MongoDB Connection Error", 500

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
    username = session['username']  # Get logged-in user

    users_collection.update_one(
        {"username": username},
        {"$set": {"cart": []}}  # Clear the cart
    )

    return jsonify({"status": "success", "message": "Checkout successful!"})

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
        username = request.form['username']
        password = request.form['password']

        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session['username'] = username
            session.permanent = True  # Keep the session active
            print(f"Logged in as: {username}")  # Debugging print
            flash("Login successful!")
            return redirect(url_for('home'))
        flash("Invalid credentials, please try again.")
    return render_template('login.html')

# Flask Route: User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if users_collection.find_one({"username": username}):
            flash("Username already exists, please choose a different one.")
        else:
            hashed_password = generate_password_hash(password)
            users_collection.insert_one({
                "username": username, 
                "password": hashed_password, 
                "cart": []
            })
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
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

# Gradio Interface
def gradio_interface():
    with gr.Blocks() as demo:
        gr.Markdown("# 🛒 Welcome to Axlen")

        # Product listing tab
        with gr.Tab("Products"):
            product_display = gr.Textbox(label="Available Products", lines=10)
            product_display.value = str(get_products())

        # Cart management tab
        with gr.Tab("Cart"):
            product_name = gr.Dropdown(
                choices=[p["name"] for p in get_products()],
                label="Select Product to Add to Cart"
            )
            add_output = gr.Textbox(label="Cart Status")
            cart_contents = gr.Textbox(label="Current Cart Contents", lines=10)
            checkout_button = gr.Button("Checkout")
            checkout_output = gr.Textbox(label="Checkout Status")

            # Callback: View Cart Contents
            def view_cart():
                response = requests.get(
                    'http://127.0.0.1:5000/get_cart', 
                    params={"username": session.get('username')}
                )
                data = response.json()
                cart = data.get('cart', [])
                total = data.get('total', 0)

                cart_display = "\n".join([f"{item['name']} - ${item['price']}" for item in cart])
                return f"{cart_display}\n\nTotal: ${total:.2f}"

            # Callback: Add product to cart
            def add_product_to_cart(product_name):
                response = requests.post(
                    'http://127.0.0.1:5000/add_to_cart',
                    json={"username": session.get('username'), "product_name": product_name}
                )
                message = response.json().get('message', 'Error adding product.')
                cart_content_after_add = view_cart()
                return message, cart_content_after_add
            
            # Callback: Perform Checkout
            def perform_checkout():
                try:
                    response = requests.post(
                        'http://127.0.0.1:5000/checkout',
                        json={"username": session.get('username')}
                    )
                    message = response.json().get('message', 'Checkout failed.')
                    # Clear the cart contents after checkout
                    return message, "Cart is empty."
                except requests.exceptions.ConnectionError:
                    return "Failed to connect to the server.", ""

            add_button = gr.Button("Add to Cart")
            add_button.click(
                add_product_to_cart,
                inputs=[product_name],
                outputs=[add_output, cart_contents]
            )

            checkout_button.click(
                perform_checkout, 
                outputs=[checkout_output, cart_contents]
            )

    return demo

# Run Flask and Gradio
if __name__ == "__main__":
    # Run Flask app in a separate process or thread
    from threading import Thread
    def run_flask():
        app.run(port=5000, threaded=False)  # Ensure Flask runs on port 5000

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Launch Gradio interface
    interface = gradio_interface()
    interface.launch(share=True)
