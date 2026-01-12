from flask import Flask, render_template, request, redirect, url_for 
from engine.database import Database
from datetime import datetime
import random
import logging

# ---------------------------
# Flask app and database
# ---------------------------
app = Flask(__name__)
db = Database()

logging.basicConfig(level=logging.INFO)

# ---------------------------
# Create tables
# ---------------------------
db.create_table("merchants", ["id", "name", "balance", "created_at"], primary_key="id")
db.create_table("customers", ["id", "name", "email", "created_at"], primary_key="id")
db.create_table(
    "transactions",
    ["id", "merchant_id", "customer_id", "amount", "status", "timestamp", "fraud_flag"],
    primary_key="id"
)

# ---------------------------
# Sample data
# ---------------------------
if not db.tables["merchants"].rows:
    db.insert("merchants", {"id": "1", "name": "Pesapal", "balance": 0, "created_at": datetime.now().strftime("%Y-%m-%d")})
if not db.tables["customers"].rows:
    db.insert("customers", {"id": "1", "name": "Ivy", "email": "ivy@example.com", "created_at": datetime.now().strftime("%Y-%m-%d")})

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
@app.route("/transactions")
def index():
    transactions = db.tables["transactions"].rows

    # Join merchant and customer names
    merchants = {m["id"]: m["name"] for m in db.tables["merchants"].rows}
    customers = {c["id"]: c["name"] for c in db.tables["customers"].rows}

    for t in transactions:
        # These will always have values because we get from dropdowns
        t["merchant_name"] = merchants.get(t["merchant_id"], "Unknown Merchant")
        t["customer_name"] = customers.get(t["customer_id"], "Unknown Customer")

    # Dashboard metrics
    total_revenue = sum(float(t["amount"]) for t in transactions if t["status"] == "complete")
    pending_count = len([t for t in transactions if t["status"] == "pending"])
    failed_count = len([t for t in transactions if t["status"] == "failed"])
    fraud_count = len([t for t in transactions if t.get("fraud_flag") == "Yes"])

    return render_template(
        "transactions.html",
        transactions=transactions,
        total_revenue=total_revenue,
        pending_count=pending_count,
        failed_count=failed_count,
        fraud_count=fraud_count
    )

@app.route("/add_transaction_page")
def add_transaction_page():
    # Dropdown values
    merchants = db.tables["merchants"].rows
    customers = db.tables["customers"].rows
    return render_template("add_transaction.html", merchants=merchants, customers=customers)

@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    # Auto-generate unique transaction ID
    id = str(random.randint(100000, 999999))
    merchant_id = request.form["merchant_id"]
    customer_id = request.form["customer_id"]

    # Validate amount
    try:
        amount = float(request.form["amount"])
        if amount <= 0:
            return "Amount must be positive", 400
    except:
        return "Invalid amount", 400

    # Validate status
    status = request.form.get("status", "pending")
    if status not in ["pending", "complete", "failed"]:
        return "Invalid status", 400

    # Fraud/high-value flag
    fraud_flag = "Yes" if amount > 10000 else "No"

    transaction = {
        "id": id,
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "amount": amount,
        "status": status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fraud_flag": fraud_flag
    }

    try:
        db.insert("transactions", transaction)
        logging.info(f"Transaction added: {transaction}")
    except ValueError as e:
        return f"Error: {str(e)}", 400

    return redirect(url_for("index"))

# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
