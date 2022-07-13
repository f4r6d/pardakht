import os, stripe, pymongo
from flask import Flask, render_template, abort, redirect, request, jsonify 

app = Flask(__name__)

stripe.api_key = os.environ.get('secret_key')
endpoint_secret = os.environ.get('endpoint_secret')
products = None
completed_order_id = None
mongo_password = os.environ.get('mongo_password')

def add_to_mongo(data):
    cluster = f'mongodb://farshid:{mongo_password}@sells-shard-00-00.ado03.mongodb.net:27017,sells-shard-00-01.ado03.mongodb.net:27017,sells-shard-00-02.ado03.mongodb.net:27017/?ssl=true&replicaSet=atlas-4l7f20-shard-0&authSource=admin&retryWrites=true&w=majority'
    client = pymongo.MongoClient(cluster)
    db = client['orders']
    ids = db['ids']
    ids.insert_one(data)


def get_products():
    tmp_products = dict()
    product_list_response = stripe.Product.list()
    for product in product_list_response['data']:
        if product["active"]:
            tmp_products[product["name"]] = {'name': product["name"], 'price': stripe.Price.retrieve(product["default_price"])["unit_amount"]}
    
    return tmp_products


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
        try:
            data = {"Order_ID": completed_order_id}
            add_to_mongo(data)
        except:
            return "MONGO ERR", data
    # ... handle other event types
    else:
        print('Unhandled event type {}'.format(event['type']))

    return jsonify(success=True)
        
   
if __name__ == "__main__":
    app.run()