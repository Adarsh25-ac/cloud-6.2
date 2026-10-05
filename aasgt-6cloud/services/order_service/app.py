import os
import requests
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Mini Database Configuration for Order Service
DB_PATH = os.environ.get('DB_PATH', '/data/orders.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Internal endpoints for sibling microservices (configured via env variables)
CATALOG_SERVICE_URL = os.environ.get('CATALOG_SERVICE_URL', 'http://catalog-service:5001')
PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL', 'http://payment-service:5003')

db = SQLAlchemy(app)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='CONFIRMED') # PENDING, CONFIRMED, FAILED
    payment_ref = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderSyncLog(db.Model):
    __tablename__ = 'order_sync_logs'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    target_service = db.Column(db.String(100), nullable=False)
    sync_status = db.Column(db.String(50), nullable=False)
    sync_payload = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "service": "Order Management Microservice",
        "vm_role": "VM3 - Order Service",
        "status": "healthy",
        "database": {
            "type": "SQLite Mini-DB",
            "total_orders": Order.query.count(),
            "sync_records": OrderSyncLog.query.count()
        },
        "connected_services": {
            "catalog_url": CATALOG_SERVICE_URL,
            "payment_url": PAYMENT_SERVICE_URL
        }
    })

@app.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return jsonify([{
        "id": o.id,
        "customer_name": o.customer_name,
        "customer_email": o.customer_email,
        "product_id": o.product_id,
        "product_name": o.product_name,
        "quantity": o.quantity,
        "unit_price": o.unit_price,
        "total_amount": o.total_amount,
        "status": o.status,
        "payment_ref": o.payment_ref,
        "created_at": o.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for o in orders])

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "product_id": order.product_id,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "unit_price": order.unit_price,
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_ref": order.payment_ref,
        "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

# Main Order Creation & Multi-DB Synchronization Coordinator
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    customer_name = data.get('customer_name', 'Customer')
    customer_email = data.get('customer_email', 'guest@example.com')
    product_id = int(data.get('product_id'))
    product_name = data.get('product_name', 'Unknown Product')
    quantity = int(data.get('quantity', 1))
    unit_price = float(data.get('unit_price', 0.0))
    total_amount = round(unit_price * quantity, 2)

    # 1. Create Initial Order in local Mini-DB
    new_order = Order(
        customer_name=customer_name,
        customer_email=customer_email,
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=total_amount,
        status='PROCESSING'
    )
    db.session.add(new_order)
    db.session.commit()

    sync_success = True
    error_reasons = []

    # 2. Inter-DB Sync #1: Deduct Stock from Catalog Service (VM 2)
    try:
        cat_resp = requests.post(
            f"{CATALOG_SERVICE_URL}/sync/deduct-stock",
            json={"product_id": product_id, "quantity": quantity, "order_id": new_order.id},
            timeout=5
        )
        if cat_resp.status_code == 200:
            db.session.add(OrderSyncLog(
                order_id=new_order.id,
                target_service="CATALOG_SERVICE_VM2",
                sync_status="SUCCESS",
                sync_payload=f"Stock deducted for product {product_id}"
            ))
        else:
            sync_success = False
            error_reasons.append(f"Catalog Sync Failed: {cat_resp.text}")
    except Exception as e:
        sync_success = False
        error_reasons.append(f"Catalog Service unreachable: {str(e)}")

    # 3. Inter-DB Sync #2: Record Payment & Replicate Ledger in Payment Service (VM 4)
    payment_ref = None
    try:
        pay_resp = requests.post(
            f"{PAYMENT_SERVICE_URL}/sync/process-payment",
            json={
                "order_id": new_order.id,
                "customer_name": customer_name,
                "amount": total_amount,
                "payment_method": "Cloud Wallet / Credit Card"
            },
            timeout=5
        )
        if pay_resp.status_code == 200:
            payment_data = pay_resp.json()
            payment_ref = payment_data.get('transaction_id')
            db.session.add(OrderSyncLog(
                order_id=new_order.id,
                target_service="PAYMENT_SERVICE_VM4",
                sync_status="SUCCESS",
                sync_payload=f"Payment verified. Txn: {payment_ref}"
            ))
        else:
            sync_success = False
            error_reasons.append(f"Payment Sync Failed: {pay_resp.text}")
    except Exception as e:
        sync_success = False
        error_reasons.append(f"Payment Service unreachable: {str(e)}")

    # 4. Finalize Order state
    if sync_success:
        new_order.status = 'CONFIRMED'
        new_order.payment_ref = payment_ref or f"TXN-{new_order.id:06d}"
    else:
        new_order.status = 'PARTIAL_SYNC_ISSUE'

    db.session.commit()

    return jsonify({
        "order_id": new_order.id,
        "status": new_order.status,
        "payment_ref": new_order.payment_ref,
        "total_amount": new_order.total_amount,
        "inter_db_sync_status": "FULL_SYNC_OK" if sync_success else "DEGRADED",
        "sync_errors": error_reasons
    }), 201

@app.route('/sync/logs', methods=['GET'])
def get_sync_logs():
    logs = OrderSyncLog.query.order_by(OrderSyncLog.id.desc()).limit(20).all()
    return jsonify([{
        "id": l.id,
        "order_id": l.order_id,
        "target_service": l.target_service,
        "sync_status": l.sync_status,
        "sync_payload": l.sync_payload,
        "timestamp": l.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for l in logs])

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002)
