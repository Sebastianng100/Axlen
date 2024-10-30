#app.config['MONGO_URI'] = "mongodb+srv://sngofficial100:T0218191b@technest.wlno2.mongodb.net/shopping?retryWrites=true&w=majority&appName=TechNest"

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_pymongo import PyMongo
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import gradio as gr
import requests

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

# Helper function to fetch all products
def get_products():
    return list(products_collection.find({}, {"_id": 0}))

# Flask Route: Add product to the cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    username = request.json.get('username')  # Identify user
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

# Flask Route: Checkout
@app.route('/checkout', methods=['POST'])
def checkout():
    username = request.json.get('username')

    users_collection.update_one(
        {"username": username},
        {"$set": {"cart": []}}  # Clear the cart
    )

    return jsonify({"status": "success", "message": "Checkout successful!"})

# Route: Display Products on Homepage
@app.route('/')
def home():
    products = get_products()
    return render_template('index.html', products=products)

# Route: View Cart
@app.route('/cart')
def view_cart():
    try:
        response = requests.get('http://127.0.0.1:5000/get_cart')
        data = response.json()
        cart = data.get('cart', [])
        total = data.get('total', 0)

        # Format the cart contents
        if cart:
            cart_display = "\n".join([f"{item['name']} - ${item['price']}" for item in cart])
        else:
            cart_display = "Your cart is empty."

        return f"{cart_display}\n\nTotal: ${total:.2f}"
    except requests.exceptions.ConnectionError:
        return "Failed to connect to the server."

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
            username = gr.Textbox(label="Enter Username")  # Collect username
            product_name = gr.Dropdown(
                choices=[p["name"] for p in get_products()],
                label="Select Product to Add to Cart"
            )
            add_output = gr.Textbox(label="Cart Status")
            cart_contents = gr.Textbox(label="Current Cart Contents", lines=10)
            checkout_button = gr.Button("Checkout")
            checkout_output = gr.Textbox(label="Checkout Status")

            # Callback: View Cart Contents for the user
            def view_cart(username):
                try:
                    response = requests.get(
                        'http://127.0.0.1:5000/get_cart', params={"username": username}
                    )
                    data = response.json()
                    cart = data.get('cart', [])
                    total = data.get('total', 0)

                    # Format cart contents and total price
                    if cart:
                        cart_display = "\n".join([f"{item['name']} - ${item['price']}" for item in cart])
                    else:
                        cart_display = "Your cart is empty."

                    return f"{cart_display}\n\nTotal: ${total:.2f}"
                except requests.exceptions.ConnectionError:
                    return "Failed to connect to the server."

            # Callback: Add product to user's cart and update cart contents
            def add_product_to_cart(username, product_name):
                try:
                    response = requests.post(
                        'http://127.0.0.1:5000/add_to_cart',
                        json={"username": username, "product_name": product_name}
                    )
                    message = response.json().get('message', 'Error adding product.')
                    # Refresh the cart contents after adding the product
                    cart_content_after_add = view_cart(username)
                    return message, cart_content_after_add
                except requests.exceptions.ConnectionError:
                    return "Failed to connect to the server.", ""

            # Hook the Add to Cart button to the callback
            add_button = gr.Button("Add to Cart")
            add_button.click(
                add_product_to_cart,  # Ensure both username and product name are passed
                inputs=[username, product_name], 
                outputs=[add_output, cart_contents]
            )

            # Callback: Checkout and clear the cart for the user
            def perform_checkout(username):
                try:
                    response = requests.post(
                        'http://127.0.0.1:5000/checkout',
                        json={"username": username}
                    )
                    # Clear the cart contents after checkout
                    return "Checkout successful! Your cart is now empty.", "Cart is empty."
                except requests.exceptions.ConnectionError:
                    return "Failed to connect to the server.", ""

            # Hook the Checkout button to the callback
            checkout_button.click(
                perform_checkout, 
                inputs=[username], 
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
