import os
import socket
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cloud-gateway-secret-2026')

# Internal IP/URL Endpoints for internal microservices (VM2, VM3, VM4)
CATALOG_SERVICE_URL = os.environ.get('CATALOG_SERVICE_URL', 'http://localhost:5001')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:5002')
PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL', 'http://localhost:5003')

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.context_processor
def inject_globals():
    return {
        'gateway_ip': get_local_ip(),
        'catalog_url': CATALOG_SERVICE_URL,
        'order_url': ORDER_SERVICE_URL,
        'payment_url': PAYMENT_SERVICE_URL
    }

# ----------------- Frontend Views -----------------

@app.route('/')
def storefront():
    products = []
    error_msg = None
    try:
        resp = requests.get(f"{CATALOG_SERVICE_URL}/products", timeout=3)
        if resp.status_code == 200:
            products = resp.json()
        else:
            error_msg = f"Catalog service returned error: {resp.status_code}"
    except Exception as e:
        error_msg = f"Could not connect to Catalog Microservice at {CATALOG_SERVICE_URL}: {str(e)}"

    return render_template('index.html', products=products, error_msg=error_msg)

@app.route('/checkout/<int:product_id>')
def checkout(product_id):
    product = None
    try:
        resp = requests.get(f"{CATALOG_SERVICE_URL}/products/{product_id}", timeout=3)
        if resp.status_code == 200:
            product = resp.json()
    except Exception:
        pass

    if not product:
        flash("Product could not be retrieved from Catalog Service.", "danger")
        return redirect(url_for('storefront'))

    return render_template('checkout.html', product=product)

@app.route('/place-order', methods=['POST'])
def place_order():
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    unit_price = request.form.get('unit_price')
    quantity = request.form.get('quantity', 1)
    customer_name = request.form.get('customer_name', 'Student')
    customer_email = request.form.get('customer_email', 'student@cloud.edu')

    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "product_id": int(product_id),
        "product_name": product_name,
        "quantity": int(quantity),
        "unit_price": float(unit_price)
    }

    try:
        resp = requests.post(f"{ORDER_SERVICE_URL}/orders", json=payload, timeout=8)
        if resp.status_code == 201:
            order_data = resp.json()
            flash(f"Order #{order_data['order_id']} placed successfully! Multi-DB Sync confirmed: {order_data['inter_db_sync_status']}. Payment Ref: {order_data['payment_ref']}", "success")
            return redirect(url_for('orders'))
        else:
            flash(f"Failed to place order: {resp.text}", "danger")
    except Exception as e:
        flash(f"Order Microservice unreachable at {ORDER_SERVICE_URL}: {str(e)}", "danger")

    return redirect(url_for('storefront'))

@app.route('/orders')
def orders():
    orders_list = []
    error_msg = None
    try:
        resp = requests.get(f"{ORDER_SERVICE_URL}/orders", timeout=3)
        if resp.status_code == 200:
            orders_list = resp.json()
        else:
            error_msg = f"Order service returned error: {resp.status_code}"
    except Exception as e:
        error_msg = f"Could not connect to Order Microservice: {str(e)}"

    return render_template('orders.html', orders=orders_list, error_msg=error_msg)

@app.route('/topology')
def topology():
    """Live Visual Dashboard of the 4 Microservices, their Mini DBs, and Sync Status"""
    def check_service(url, name, role):
        try:
            r = requests.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                data = r.json()
                return {
                    "name": name,
                    "role": role,
                    "url": url,
                    "status": "ONLINE",
                    "details": data
                }
            return {"name": name, "role": role, "url": url, "status": "DEGRADED", "details": r.text}
        except Exception as e:
            return {"name": name, "role": role, "url": url, "status": "OFFLINE", "error": str(e)}

    catalog_health = check_service(CATALOG_SERVICE_URL, "Catalog & Inventory Service", "VM 2")
    order_health = check_service(ORDER_SERVICE_URL, "Order Management Service", "VM 3")
    payment_health = check_service(PAYMENT_SERVICE_URL, "Payment & Sync Service", "VM 4")

    # Fetch recent sync logs
    sync_overview = {}
    try:
        sync_resp = requests.get(f"{PAYMENT_SERVICE_URL}/sync/overview", timeout=2)
        if sync_resp.status_code == 200:
            sync_overview = sync_resp.json()
    except Exception:
        pass

    return render_template(
        'topology.html',
        catalog_health=catalog_health,
        order_health=order_health,
        payment_health=payment_health,
        sync_overview=sync_overview
    )

# ----------------- API Gateway Proxy Endpoints -----------------

@app.route('/api/catalog/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_catalog(path):
    url = f"{CATALOG_SERVICE_URL}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=5
        )
        return (resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        return jsonify({"error": f"Catalog service error: {str(e)}"}), 502

@app.route('/api/orders/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_orders(path):
    url = f"{ORDER_SERVICE_URL}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=5
        )
        return (resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        return jsonify({"error": f"Order service error: {str(e)}"}), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
