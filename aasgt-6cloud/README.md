# Cloud Computing Practical 6.2: 4-Microservice Distributed E-Commerce Architecture

This project implements **Experiment 6.2** on **Google Cloud Platform (GCP)**:
- **Maximum 4 Microservices**, each with its own **Mini Database** hosted across **4 separate Virtual Machines**.
- **Security Constraint:** Only the **API Gateway / Frontend (VM 1)** is exposed through an **External IP** (`port 5000`). All other microservices (VM 2, VM 3, VM 4) are strictly accessible only via **VPC Internal IPs**.
- **Inter-Database Synchronization:** Automated cross-database synchronization between Catalog DB, Order DB, and Payment DB upon checkout.

---

## 🏛️ Architecture Overview

```
                          [ Public Internet / Browser ]
                                        │
                                        ▼ (Port 5000 / External IP)
┌─────────────────────────────────────────────────────────────────────────┐
│ VM 1: API Gateway & Storefront UI (ecom-gateway-vm)                    │
│  • Public IP: Exposed to external traffic                               │
│  • Internal IP: 10.x.x.1                                                │
│  • Role: Reverse Proxy, Session Routing & Real-Time Topology Dashboard  │
└────────────────┬───────────────────┬───────────────────┬────────────────┘
                 │                   │                   │
  Internal IP    │      Internal IP  │      Internal IP  │
  Port: 5001     │      Port: 5002   │      Port: 5003   │
                 ▼                   ▼                   ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ VM 2: Catalog Service│ │ VM 3: Order Service  │ │ VM 4: Payment Service│
│ (ecom-catalog-vm)    │ │ (ecom-order-vm)      │ │ (ecom-payment-vm)    │
│                      │ │                      │ │                      │
│ • Internal IP only   │ │ • Internal IP only   │ │ • Internal IP only   │
│ • Mini-DB:           │ │ • Mini-DB:           │ │ • Mini-DB:           │
│   catalog.db         │ │   orders.db          │ │   payments.db        │
└──────────┬───────────┘ └──────────┬───────────┘ └──────────┬───────────┘
           │                        │                        │
           └────────────────────────┴────────────────────────┘
                 🔄 Cross-Database Sync & Event Reconciliation
```

---

## 📁 Repository Structure

```
.
├── services/
│   ├── gateway/                  # VM 1: Frontend & API Gateway (Port 5000)
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── static/style.css
│   │   └── templates/ (index.html, checkout.html, orders.html, topology.html)
│   ├── catalog_service/          # VM 2: Product Catalog & Stock (Port 5001) + Mini-DB
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── order_service/            # VM 3: Order Management & Sync (Port 5002) + Mini-DB
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── payment_sync_service/     # VM 4: Payment Ledger & DB Sync (Port 5003) + Mini-DB
│       ├── app.py
│       ├── Dockerfile
│       └── requirements.txt
├── docker-compose.yml            # Local / single-host compose test stack
└── README.md
```

---

## 🏷️ GCP Virtual Machines & Service Roles

| Virtual Machine | Recommended GCP Name | Internal Port | External IP? | Mini Database | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VM 1** | **`ecom-gateway-vm`** | `5000` | **YES (Public)** | — | Serves Web Storefront & routes API traffic |
| **VM 2** | **`ecom-catalog-vm`** | `5001` | **NO (Internal Only)** | `catalog.db` | Manages stock & product records |
| **VM 3** | **`ecom-order-vm`** | `5002` | **NO (Internal Only)** | `orders.db` | Manages customer orders & sync dispatch |
| **VM 4** | **`ecom-payment-vm`** | `5003` | **NO (Internal Only)** | `payments.db` | Manages payment transactions & sync log |

---

## 🔄 Cross-Database Synchronization Workflow

When a user buys a product on the Gateway:
1. **VM 3 (Order Service)** inserts the new order into `orders.db` with state `PROCESSING`.
2. **Sync Event 1 (Order &rarr; Catalog VM 2):** Calls `/sync/deduct-stock` on VM 2. VM 2 atomically deducts product stock in `catalog.db` and writes an audit sync record.
3. **Sync Event 2 (Order &rarr; Payment VM 4):** Calls `/sync/process-payment` on VM 4. VM 4 creates a transaction entry in `payments.db` and records the cross-DB reconciliation.
4. **VM 3 (Order Service)** marks the order `CONFIRMED` with the generated Payment Reference.
5. All 4 services stay synchronized and can be monitored live via the **Topology & DB Sync Dashboard** at `/topology`.

---

## 🚀 Step-by-Step GCP Deployment Guide

### Step 1: Create 4 VMs in the Same Region/Zone (e.g. `us-central1-a`)
- **VM 1 (`ecom-gateway-vm`):** e2-micro, Ubuntu 22.04 LTS, Check "Allow HTTP traffic"
- **VM 2 (`ecom-catalog-vm`):** e2-micro, Ubuntu 22.04 LTS
- **VM 3 (`ecom-order-vm`):** e2-micro, Ubuntu 22.04 LTS
- **VM 4 (`ecom-payment-vm`):** e2-micro, Ubuntu 22.04 LTS

*Note down their internal IPs from the GCP Console (e.g., VM1: `10.128.0.2`, VM2: `10.128.0.3`, VM3: `10.128.0.4`, VM4: `10.128.0.5`).*

---

### Step 2: Allow Port 5000 on GCP Firewall (for Gateway VM only)
Run in Google Cloud Shell:
```bash
gcloud compute firewall-rules create allow-ecom-gateway \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:5000 \
    --source-ranges=0.0.0.0/0
```

---

### Step 3: Deploy VM 4 (`ecom-payment-vm`)
SSH into **VM 4**:
```bash
git clone https://github.com/Adarsh25-ac/cloud-assgt-6.git
cd cloud-assgt-6/services/payment_sync_service

sudo docker build -t ecom-payment-service .
sudo docker run -d --name ecom-payment-service --restart always -p 5003:5003 ecom-payment-service
```

---

### Step 4: Deploy VM 2 (`ecom-catalog-vm`)
SSH into **VM 2**:
```bash
git clone https://github.com/Adarsh25-ac/cloud-assgt-6.git
cd cloud-assgt-6/services/catalog_service

sudo docker build -t ecom-catalog-service .
sudo docker run -d --name ecom-catalog-service --restart always -p 5001:5001 ecom-catalog-service
```

---

### Step 5: Deploy VM 3 (`ecom-order-vm`)
SSH into **VM 3** *(provide VM2 and VM4 internal IPs)*:
```bash
git clone https://github.com/Adarsh25-ac/cloud-assgt-6.git
cd cloud-assgt-6/services/order_service

sudo docker build -t ecom-order-service .
sudo docker run -d \
  --name ecom-order-service \
  --restart always \
  -p 5002:5002 \
  -e CATALOG_SERVICE_URL="http://<VM2_INTERNAL_IP>:5001" \
  -e PAYMENT_SERVICE_URL="http://<VM4_INTERNAL_IP>:5003" \
  ecom-order-service
```

---

### Step 6: Deploy VM 1 (`ecom-gateway-vm`)
SSH into **VM 1** *(provide VM2, VM3, VM4 internal IPs)*:
```bash
git clone https://github.com/Adarsh25-ac/cloud-assgt-6.git
cd cloud-assgt-6/services/gateway

sudo docker build -t ecom-gateway .
sudo docker run -d \
  --name ecom-gateway \
  --restart always \
  -p 5000:5000 \
  -e CATALOG_SERVICE_URL="http://<VM2_INTERNAL_IP>:5001" \
  -e ORDER_SERVICE_URL="http://<VM3_INTERNAL_IP>:5002" \
  -e PAYMENT_SERVICE_URL="http://<VM4_INTERNAL_IP>:5003" \
  ecom-gateway
```

---

### 🧪 Verification & Demonstration
1. Open your browser: `http://<VM1_EXTERNAL_IP>:5000`
2. Click **⚡ Live Architecture & DB Sync** to view the live health and cross-DB sync monitor.
3. Click **Buy Now** on a product and place an order.
4. Verify:
   - Order is created in **VM 3 (Order DB)**.
   - Stock is decremented in **VM 2 (Catalog DB)**.
   - Transaction is logged in **VM 4 (Payment DB)**.
