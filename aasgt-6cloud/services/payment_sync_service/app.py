import os
import uuid
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Mini Database Configuration for Payment & Sync Service
DB_PATH = os.environ.get('DB_PATH', '/data/payments.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class PaymentLedger(db.Model):
    __tablename__ = 'payment_ledger'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    order_id = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(80), default='Cloud Wallet')
    status = db.Column(db.String(40), default='SUCCESS')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class CrossDbSyncRecord(db.Model):
    __tablename__ = 'cross_db_sync_records'
    id = db.Column(db.Integer, primary_key=True)
    source_service = db.Column(db.String(100), default='ORDER_SERVICE_VM3')
    target_service = db.Column(db.String(100), default='PAYMENT_SERVICE_VM4')
    entity_type = db.Column(db.String(50), default='ORDER_TRANSACTION')
    entity_id = db.Column(db.String(50))
    sync_status = db.Column(db.String(30), default='RECONCILED')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "service": "Payment & Ledger Microservice",
        "vm_role": "VM4 - Payment & Sync Service",
        "status": "healthy",
        "database": {
            "type": "SQLite Mini-DB",
            "total_transactions": PaymentLedger.query.count(),
            "sync_records_count": CrossDbSyncRecord.query.count()
        }
    })

@app.route('/payments', methods=['GET'])
def get_payments():
    payments = PaymentLedger.query.order_by(PaymentLedger.id.desc()).all()
    return jsonify([{
        "id": p.id,
        "transaction_id": p.transaction_id,
        "order_id": p.order_id,
        "customer_name": p.customer_name,
        "amount": p.amount,
        "payment_method": p.payment_method,
        "status": p.status,
        "timestamp": p.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for p in payments])

# Inter-Service DB Sync Endpoint: Process Payment & record ledger entry
@app.route('/sync/process-payment', methods=['POST'])
def process_payment():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    customer_name = data.get('customer_name', 'Customer')
    amount = float(data.get('amount', 0.0))
    payment_method = data.get('payment_method', 'Cloud Pay')

    txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"

    # Record in Payment Mini-DB
    payment = PaymentLedger(
        transaction_id=txn_id,
        order_id=order_id,
        customer_name=customer_name,
        amount=amount,
        payment_method=payment_method,
        status='SUCCESS'
    )
    db.session.add(payment)

    # Record cross-db synchronization reconciliation
    sync_record = CrossDbSyncRecord(
        source_service='ORDER_SERVICE_VM3',
        target_service='PAYMENT_SERVICE_VM4',
        entity_type='ORDER_PAYMENT_SYNC',
        entity_id=str(order_id),
        sync_status='RECONCILED'
    )
    db.session.add(sync_record)
    db.session.commit()

    return jsonify({
        "status": "payment_approved",
        "transaction_id": txn_id,
        "order_id": order_id,
        "amount": amount,
        "sync_record_id": sync_record.id
    })

@app.route('/sync/overview', methods=['GET'])
def get_sync_overview():
    records = CrossDbSyncRecord.query.order_by(CrossDbSyncRecord.id.desc()).limit(20).all()
    return jsonify({
        "total_synced_transactions": PaymentLedger.query.count(),
        "total_cross_db_records": CrossDbSyncRecord.query.count(),
        "recent_syncs": [{
            "id": r.id,
            "source": r.source_service,
            "target": r.target_service,
            "entity_id": r.entity_id,
            "status": r.sync_status,
            "created_at": r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for r in records]
    })

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5003)
