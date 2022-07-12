import os
from flask import Flask, render_template, abort, redirect, request
import stripe

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


@app.route('/event', methods=['POST'])
def new_event():
    event = None
    payload = request.data
    signature = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, stripe.api_key)
    except Exception as e:
        # the payload could not be verified
        abort(400)


    if event['type'] == 'payment_intent.succeeded':
        global completed_order_id
        completed_order_id = event['data']['object']['id']
    else:
        print('Unhandled event type {}'.format(event['type']))

    return {'success': True}


if __name__ == "__main__":
    app.run()