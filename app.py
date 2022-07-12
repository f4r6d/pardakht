import os
from flask import Flask, render_template, abort, redirect, request, jsonify
import stripe, json

app = Flask(__name__)
stripe.api_key = "sk_test_51LKMv5J3ofAqn0Rk13O8Zkja2jvjVCeO1w6dLoN8tC8gi8SFcyY0WY6PeujJqmpVibmqWDMpoYqvNoBYZCftci5J00OgVmlQhq"

completed_order_id = None

def get_products():
    tmp_products = dict()
    product_list_response = stripe.Product.list()
    for product in product_list_response['data']:
        if product["active"]:
            tmp_products[product["name"]] = {'name': product["name"], 'price': stripe.Price.retrieve(product["default_price"])["unit_amount"]}
    
    return tmp_products

products = get_products()

@app.route('/')
def index():
    global products
    products = get_products()
    return render_template('index.html', products=products)


@app.route('/order/<product_id>', methods=['POST'])
def order(product_id):
    if product_id not in products:
        abort(404)

    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                'price_data': {
                    'product_data': {
                        'name': products[product_id]['name'],
                    },
                    'unit_amount': products[product_id]['price'],
                    'currency': 'usd',
                },
                'quantity': 1,
            },
        ],
        payment_method_types=['card'],
        mode='payment',
        success_url=request.host_url + 'order/success',
        cancel_url=request.host_url + 'order/cancel',
    )
    return redirect(checkout_session.url)


@app.route('/order/success')
def success():
    return render_template('success.html', completed_order_id=completed_order_id)


@app.route('/order/cancel')
def cancel():
    return render_template('cancel.html')


# app.py
#
# Use this sample code to handle webhook events in your integration.
#
# 1) Paste this code into a new file (app.py)
#
# 2) Install dependencies
#   pip3 install flask
#   pip3 install stripe
#
# 3) Run the server on http://localhost:4242
#   python3 -m flask run --port=4242


endpoint_secret = 'whsec_Kaj3M5lCu59OmwIjDPS4x4ffS7y6aL6h'

@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        global completed_order_id
        completed_order_id = event['data']['object']['id']
    # ... handle other event types
    else:
        print('Unhandled event type {}'.format(event['type']))

    return jsonify(success=True)
        
   


if __name__ == "__main__":
    app.run()