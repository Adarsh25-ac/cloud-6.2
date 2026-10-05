import os
import requests
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Mini Database Configuration for Catalog Service
DB_PATH = os.environ.get('DB_PATH', '/data/catalog.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=10)
    category = db.Column(db.String(50), default='General')
    image_url = db.Column(db.String(300), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CatalogSyncLog(db.Model):
    __tablename__ = 'catalog_sync_logs'
    id = db.Column(db.Integer, primary_key=True)
    sync_event = db.Column(db.String(100), nullable=False)
    reference_id = db.Column(db.String(100))
    details = db.Column(db.Text)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

def seed_initial_products():
    if Product.query.count() == 0:
        sample_items = [
            Product(
                name="Cloud Native Mechanical Keyboard",
                description="RGB wireless mechanical keyboard with hot-swappable switches.",
                price=89.99,
                stock=15,
                category="Accessories",
                image_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80"
            ),
            Product(
                name="Ultra HD 4K Developer Monitor",
                description="27-inch IPS USB-C 4K HDR monitor with ergonomic stand.",
                price=349.99,
                stock=8,
                category="Displays",
                image_url="https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&q=80"
            ),
            Product(
                name="Noise Cancelling Wireless Headphones",
                description="Active noise cancelling studio over-ear headphones with 30h battery.",
                price=199.99,
                stock=20,
                category="Audio",
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80"
            ),
            Product(
                name="Ergonomic Mesh Office Chair",
                description="High-back lumbar support breathable mesh chair for long coding sessions.",
                price=249.99,
                stock=5,
                category="Furniture",
                image_url="https://images.unsplash.com/photo-1580481077197-047b85e054b7?auto=format&fit=crop&w=600&q=80"
            )
        ]
        db.session.bulk_save_objects(sample_items)
        db.session.commit()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "service": "Catalog & Inventory Microservice",
        "vm_role": "VM2 - Catalog Service",
        "status": "healthy",
        "database": {
            "type": "SQLite Mini-DB",
            "total_products": Product.query.count(),
            "sync_events_recorded": CatalogSyncLog.query.count()
        }
    })

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "price": p.price,
        "stock": p.stock,
        "category": p.category,
        "image_url": p.image_url
    } for p in products])

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "category": product.category,
        "image_url": product.image_url
    })

# Inter-Service DB Sync Endpoint: Deduct inventory when order is placed
@app.route('/sync/deduct-stock', methods=['POST'])
def deduct_stock():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    order_id = data.get('order_id')
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    if product.stock < quantity:
        return jsonify({"error": f"Insufficient stock. Available: {product.stock}"}), 400
        
    product.stock -= quantity
    
    # Log sync event in Catalog mini DB
    sync_log = CatalogSyncLog(
        sync_event="STOCK_DEDUCTED_BY_ORDER_SYNC",
        reference_id=str(order_id),
        details=f"Deducted {quantity} units of '{product.name}' for Order #{order_id}. Remaining stock: {product.stock}"
    )
    db.session.add(sync_log)
    db.session.commit()
    
    return jsonify({
        "status": "synced",
        "product_id": product.id,
        "remaining_stock": product.stock,
        "sync_log_id": sync_log.id
    })

@app.route('/sync/logs', methods=['GET'])
def get_sync_logs():
    logs = CatalogSyncLog.query.order_by(CatalogSyncLog.id.desc()).limit(20).all()
    return jsonify([{
        "id": l.id,
        "event": l.sync_event,
        "reference_id": l.reference_id,
        "details": l.details,
        "synced_at": l.synced_at.strftime('%Y-%m-%d %H:%M:%S')
    } for l in logs])

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with app.app_context():
        db.create_all()
        seed_initial_products()
    app.run(host='0.0.0.0', port=5001)
