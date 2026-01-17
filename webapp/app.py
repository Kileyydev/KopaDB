from flask import Flask, render_template, request, redirect, url_for, session, flash
from engine.database import Database
from datetime import datetime, timedelta
import random
import logging
import hashlib

app = Flask(__name__)
app.secret_key = "super-secret-key-please-change-this-in-production-2026!!!"  # CHANGE THIS IN PROD!

db = Database()
logging.basicConfig(level=logging.INFO)

# ---------------------------
# Create tables (idempotent)
# ---------------------------
tables_to_create = {
    "merchants": {
        "columns": ["id", "name", "email", "password_hash", "balance", "created_at"],
        "primary_key": "id"
    },
    "customers": {
        "columns": ["id", "name", "email", "password_hash", "created_at", "risk_score", "wallet_balance",
                    "current_package_id", "last_good_repayment"],  # added for tier system
        "primary_key": "id"
    },
    "transactions": {
        "columns": ["id", "merchant_id", "customer_id", "amount", "interest_rate", "repayment_days",
                    "status", "timestamp", "fraud_flag", "due_date"],
        "primary_key": "id"
    },
    "loan_packages": {
        "columns": ["id", "merchant_id", "name", "max_amount", "interest_rate", "repayment_days",
                    "min_risk_score", "order_level", "created_at"],
        "primary_key": "id"
    }
}

for table_name, config in tables_to_create.items():
    if table_name not in db.tables:
        db.create_table(
            table_name,
            config["columns"],
            primary_key=config.get("primary_key")
        )
        logging.info(f"Created table: {table_name}")
    else:
        logging.info(f"Table {table_name} already exists - skipping")

# Migrate existing customers to have new fields (safe to run multiple times)
for cust in db.tables["customers"].rows:
    if "current_package_id" not in cust:
        cust["current_package_id"] = None
    if "last_good_repayment" not in cust:
        cust["last_good_repayment"] = None
db._save_data()

# ---------------------------
# Sample data
# ---------------------------
if not db.tables["merchants"].rows:
    db.insert("merchants", {
        "id": "1",
        "name": "Pesapal",
        "email": "pesapal@example.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "balance": 1000000.0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    db._save_data()

if not db.tables["customers"].rows:
    db.insert("customers", {
        "id": "1",
        "name": "Ivy",
        "email": "ivy@example.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "risk_score": 0,
        "wallet_balance": 0.0,
        "current_package_id": None,
        "last_good_repayment": None
    })
    db._save_data()

# ---------------------------
# Helper: Update overdue loans
# ---------------------------
def update_overdue_loans():
    today = datetime.now().date()
    updated = False

    for t in db.tables["transactions"].rows:
        if t.get("status") == "accepted":
            if "due_date" not in t or not t["due_date"]:
                continue
            try:
                due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
                if due < today:
                    customer = next((c for c in db.tables["customers"].rows if c["id"] == t["customer_id"]), None)
                    if customer:
                        old_score = int(customer.get("risk_score", 0))
                        customer["risk_score"] = min(2, old_score + 1)
                        t["status"] = "failed"
                        t["fraud_flag"] = "Overdue - Risk Increased"
                        updated = True
                        logging.info(f"Loan {t['id']} overdue → failed, risk updated")
            except ValueError:
                continue

    if updated:
        db._save_data()

# ---------------------------
# Helper: Try to upgrade customer tier
# ---------------------------
def try_upgrade_customer(customer_id, merchant_id):
    customer = next((c for c in db.tables["customers"].rows if c["id"] == customer_id), None)
    if not customer:
        return False

    current_pkg_id = customer.get("current_package_id")
    current_level = 0

    if current_pkg_id:
        pkg = next((p for p in db.tables["loan_packages"].rows if p["id"] == current_pkg_id), None)
        if pkg:
            current_level = pkg.get("order_level", 1)

    # Find next tier
    next_pkg = next(
        (p for p in db.tables["loan_packages"].rows
         if p["merchant_id"] == merchant_id
         and p.get("order_level", 999) == current_level + 1),
        None
    )

    if not next_pkg:
        return False

    # Count good recent loans (simple rule: ≥2 accepted & not overdue)
    recent_loans = [
        t for t in db.tables["transactions"].rows
        if t["customer_id"] == customer_id
        and t["merchant_id"] == merchant_id
        and t["status"] in ["accepted", "complete"]  # adjust if you use "complete"
    ]
    recent_loans = sorted(recent_loans, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]

    good_count = 0
    for loan in recent_loans:
        if "due_date" in loan and loan["due_date"]:
            try:
                due = datetime.strptime(loan["due_date"], "%Y-%m-%d")
                if due >= datetime.now().date():
                    good_count += 1
            except:
                pass

    if good_count >= 2:
        customer["current_package_id"] = next_pkg["id"]
        customer["last_good_repayment"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db._save_data()
        logging.info(f"Customer {customer_id} upgraded to {next_pkg.get('name', 'Unknown')}")
        return True

    return False

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        user = next((m for m in db.tables["merchants"].rows if m.get("email") == email and m.get("password_hash") == password_hash), None)
        user_type = "merchant"

        if not user:
            user = next((c for c in db.tables["customers"].rows if c.get("email") == email and c.get("password_hash") == password_hash), None)
            user_type = "customer"

        if user:
            session.clear()
            session['user_id'] = user["id"]
            session['user_type'] = user_type
            session['user_name'] = user["name"]
            session['email'] = user.get("email")
            flash("Login successful! Welcome back.", "success")
            return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("landing"))

@app.route("/dashboard")
def user_dashboard():
    if 'user_id' not in session:
        flash("Please login to access your dashboard", "error")
        return redirect(url_for("login"))

    update_overdue_loans()

    user_id = session['user_id']
    user_type = session['user_type']
    user_name = session.get('user_name', 'User')
    current_date = datetime.now().strftime("%Y-%m-%d")

    if user_type == "merchant":
        merchant = next((m for m in db.tables["merchants"].rows if m["id"] == user_id), None)
        if not merchant:
            session.clear()
            return redirect(url_for("login"))

        transactions = [t for t in db.tables["transactions"].rows if t["merchant_id"] == user_id]

        return render_template(
            "dashboard_merchant.html",
            user_name=user_name,
            balance=merchant.get("balance", 0.0),
            transactions=transactions,
            user_type="merchant",
            current_date=current_date,
            current_year=datetime.now().year
        )

    elif user_type == "customer":
        customer = next((c for c in db.tables["customers"].rows if c["id"] == user_id), None)
        if not customer:
            session.clear()
            return redirect(url_for("login"))

        merchants = db.tables["merchants"].rows

        transactions = [t for t in db.tables["transactions"].rows if t["customer_id"] == user_id]
        merchant_names = {m["id"]: m["name"] for m in merchants}
        for t in transactions:
            t["merchant_name"] = merchant_names.get(t["merchant_id"], "Unknown")

        return render_template(
            "dashboard_customer.html",
            user_name=user_name,
            merchants=merchants,
            transactions=transactions,
            wallet_balance=customer.get("wallet_balance", 0.0),
            user_type="customer",
            current_date=current_date,
            current_year=datetime.now().year
        )

    session.clear()
    return redirect(url_for("login"))

# ────────────────────────────────────────────────
# NEW: Merchant Loan Packages Management
# ────────────────────────────────────────────────
@app.route("/merchant/packages", methods=["GET", "POST"])

@app.route("/merchant_packages", methods=["GET", "POST"])

# Assume db is your KopaDB Database object
# db = Database()

@app.route("/merchant/packages", methods=["GET", "POST"])
def merchant_packages():
    if 'user_id' not in session or session.get('user_type') != "merchant":
        flash("Merchant login required", "error")
        return redirect(url_for("login"))

    merchant_id = session['user_id']

    if request.method == "POST":
        action = request.form.get("action")
        pkg_id = request.form.get("package_id")

        if action == "create":
            # CREATE
            name = request.form.get("name", "").strip()
            try:
                max_amount = float(request.form.get("max_amount", 0))
                interest = float(request.form.get("interest_rate", 0))
                days = int(request.form.get("repayment_days", 0))
                min_risk = int(request.form.get("min_risk_score", 0))
                level = int(request.form.get("order_level", 1))
            except ValueError:
                flash("Numbers must be valid", "error")
                return redirect(url_for("merchant_packages"))

            if not name or max_amount <= 0 or interest <= 0 or days <= 0:
                flash("Fill required fields: name, max amount, interest, repayment days", "error")
            else:
                new_pkg = {
                    "id": str(random.randint(100000, 999999)),
                    "merchant_id": merchant_id,
                    "name": name,
                    "max_amount": max_amount,
                    "interest_rate": interest,
                    "repayment_days": days,
                    "min_risk_score": min_risk,
                    "order_level": level,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                db.insert("loan_packages", new_pkg)
                db._save_data()
                flash(f"Package '{name}' created!", "success")

        elif action == "edit":
            # EDIT
            package = next((p for p in db.tables["loan_packages"].rows if p["id"] == pkg_id), None)
            if not package:
                flash("Package not found", "error")
            else:
                # Update only if fields exist in form
                name = request.form.get("name")
                if name:
                    package["name"] = name.strip()
                max_amount = request.form.get("max_amount")
                if max_amount:
                    package["max_amount"] = float(max_amount)
                interest = request.form.get("interest_rate")
                if interest:
                    package["interest_rate"] = float(interest)
                days = request.form.get("repayment_days")
                if days:
                    package["repayment_days"] = int(days)
                min_risk = request.form.get("min_risk_score")
                if min_risk:
                    package["min_risk_score"] = int(min_risk)
                level = request.form.get("order_level")
                if level:
                    package["order_level"] = int(level)
                db._save_data()
                flash(f"Package '{package['name']}' updated!", "success")

        elif action == "delete":
            # DELETE
            db.tables["loan_packages"].rows = [
                p for p in db.tables["loan_packages"].rows if p["id"] != pkg_id
            ]
            db._save_data()
            flash("Package deleted successfully!", "success")

    # GET: fetch all packages
    packages = [p for p in db.tables["loan_packages"].rows if p["merchant_id"] == merchant_id]
    packages.sort(key=lambda x: x.get("order_level", 999))

    return render_template("merchant_packages.html", packages=packages, user_name=session.get('user_name'))


@app.route("/register_merchant", methods=["GET", "POST"])
def register_merchant():
    if request.method == "POST":
        try:
            merchant_id = str(random.randint(1000, 9999))
            name = request.form["name"]
            email = request.form["email"]
            password = request.form["password"]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            balance = float(request.form.get("balance", 1_000_000.0))
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            merchant = {
                "id": merchant_id,
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "balance": balance,
                "created_at": created_at
            }

            db.insert("merchants", merchant)
            db._save_data()

            session.clear()
            session['user_id'] = merchant_id
            session['user_type'] = "merchant"
            session['user_name'] = name
            session['email'] = email

            flash("Merchant account created! Welcome.", "success")
            return redirect(url_for("user_dashboard"))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template("register_merchant.html")

@app.route("/register_customer", methods=["GET", "POST"])
def register_customer():
    if request.method == "POST":
        try:
            customer_id = str(random.randint(1000, 9999))
            name = request.form["name"]
            email = request.form["email"]
            password = request.form["password"]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            credit_score = random.randint(300, 850)
            late_payments = random.uniform(0, 0.6)
            risk_score = 0
            if credit_score < 580 or late_payments > 0.35:
                risk_score = 2
            elif credit_score < 680 or late_payments > 0.15:
                risk_score = 1

            customer = {
                "id": customer_id,
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "created_at": created_at,
                "risk_score": risk_score,
                "wallet_balance": 0.0,
                "current_package_id": None,
                "last_good_repayment": None
            }

            db.insert("customers", customer)
            db._save_data()

            session.clear()
            session['user_id'] = customer_id
            session['user_type'] = "customer"
            session['user_name'] = name
            session['email'] = email

            flash(f"Account created! Risk Score: {risk_score}", "success")
            return redirect(url_for("user_dashboard"))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template("register_customer.html")

@app.route("/request_loan/<merchant_id>", methods=["GET", "POST"])


@app.route("/customer/request_loan/<merchant_id>", methods=["GET", "POST"])


def request_loan(merchant_id):
    # Ensure customer is logged in
    if 'user_id' not in session or session.get('user_type') != "customer":
        flash("Please login as customer", "error")
        return redirect(url_for("login"))

    customer_id = session['user_id']

    # Fetch customer and merchant
    customer = next((c for c in db.tables["customers"].rows if c["id"] == customer_id), None)
    merchant = next((m for m in db.tables["merchants"].rows if m["id"] == merchant_id), None)

    if not customer or not merchant:
        flash("Invalid request", "error")
        return redirect(url_for("user_dashboard"))

    # Ensure numeric fields for customer
    try:
        customer["risk_score"] = int(customer.get("risk_score", 0))
        customer["current_package_id"] = customer.get("current_package_id")  # keep as is
    except (ValueError, TypeError):
        customer["risk_score"] = 0

    # Ensure merchant balance is float
    try:
        merchant["balance"] = float(merchant.get("balance", 0))
    except (ValueError, TypeError):
        merchant["balance"] = 0.0

    # Get merchant packages
    packages = [p for p in db.tables["loan_packages"].rows if p["merchant_id"] == merchant_id]

    # Sort and ensure numeric fields
    for pkg in packages:
        try:
            pkg["max_amount"] = float(pkg.get("max_amount", 0))
            pkg["interest_rate"] = float(pkg.get("interest_rate", 0))
            pkg["repayment_days"] = int(pkg.get("repayment_days", 0))
            pkg["min_risk_score"] = int(pkg.get("min_risk_score", 0))
            pkg["order_level"] = int(pkg.get("order_level", 1))
        except (ValueError, TypeError):
            pkg["max_amount"] = 0.0
            pkg["interest_rate"] = 0.0
            pkg["repayment_days"] = 0
            pkg["min_risk_score"] = 0
            pkg["order_level"] = 1

    packages.sort(key=lambda x: x.get("order_level", 999))

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            if amount <= 0:
                flash("Amount must be positive", "error")
                return redirect(request.url)

            # Determine current package
            pkg = None
            current_pkg_id = customer.get("current_package_id")

            if current_pkg_id:
                pkg = next((p for p in packages if p["id"] == current_pkg_id), None)

            if not pkg and packages:
                pkg = min(packages, key=lambda x: x.get("order_level", 999))
                customer["current_package_id"] = pkg["id"]
                db._save_data()
                flash("You've been placed in the Starter package.", "info")

            # Set constraints
            if pkg:
                max_allowed = pkg["max_amount"]
                interest_rate = pkg["interest_rate"]
                repayment_days = pkg["repayment_days"]
            else:
                max_allowed = 20000.0
                interest_rate = 18.0
                repayment_days = 30

            if amount > max_allowed:
                flash(f"Your current package allows max KES {max_allowed:,.0f}", "error")
                return redirect(request.url)

            if amount > merchant["balance"]:
                flash("Merchant has insufficient balance", "error")
                return redirect(request.url)

            due_date = (datetime.now() + timedelta(days=repayment_days)).strftime("%Y-%m-%d")

            # Save transaction
            loan_id = str(random.randint(100000, 999999))
            transaction = {
                "id": loan_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "amount": amount,
                "interest_rate": interest_rate,
                "repayment_days": repayment_days,
                "status": "pending",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fraud_flag": f"Risk: {customer.get('risk_score', 'N/A')}",
                "due_date": due_date
            }

            db.insert("transactions", transaction)
            db._save_data()

            flash(f"Loan request of KES {amount:,.2f} sent!", "success")
            return redirect(url_for("user_dashboard"))

        except ValueError as e:
            flash(f"Invalid amount: {str(e)}", "error")
            return redirect(request.url)

    return render_template(
        "request_loan.html",
        merchant=merchant,
        customer=customer,
        packages=packages,
        default_interest=18  # fallback interest
    )

# The rest of your routes remain unchanged
@app.route("/merchant_loans")
def merchant_loans():
    if 'user_id' not in session or session['user_type'] != "merchant":
        flash("Please login as merchant", "error")
        return redirect(url_for("login"))

    merchant_id = session['user_id']
    pending_loans = [
        t for t in db.tables["transactions"].rows 
        if t["merchant_id"] == merchant_id and t["status"] == "pending"
    ]

    customers = {c["id"]: c for c in db.tables["customers"].rows}
    for loan in pending_loans:
        c = customers.get(loan["customer_id"])
        loan["customer_name"] = c["name"] if c else "Unknown"
        loan["risk_score"] = c.get("risk_score", "N/A") if c else "N/A"

    return render_template("merchant_loans.html", pending_loans=pending_loans, user_name=session['user_name'])

@app.route("/loan_action/<loan_id>/<action>", methods=["POST"])
def loan_action(loan_id, action):
    if 'user_id' not in session or session['user_type'] != "merchant":
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    merchant_id = session['user_id']
    loan = next((t for t in db.tables["transactions"].rows if t["id"] == loan_id), None)

    if not loan or loan["merchant_id"] != merchant_id or loan["status"] != "pending":
        flash("Invalid loan", "error")
        return redirect(url_for("merchant_loans"))

    amount = float(loan["amount"])

    if action == "approve":
        merchant = next((m for m in db.tables["merchants"].rows if m["id"] == merchant_id), None)
        if not merchant or merchant["balance"] < amount:
            flash("Insufficient balance", "error")
            return redirect(url_for("merchant_loans"))

        merchant["balance"] -= amount
        customer = next((c for c in db.tables["customers"].rows if c["id"] == loan["customer_id"]), None)
        if customer:
            customer["wallet_balance"] = float(customer.get("wallet_balance", 0)) + amount

        loan["status"] = "accepted"
        loan["fraud_flag"] = "Approved"
        flash("Loan approved & funds transferred!", "success")

    elif action == "reject":
        loan["status"] = "failed"
        loan["fraud_flag"] = "Rejected"
        flash("Loan rejected.", "info")

    db._save_data()
    return redirect(url_for("merchant_loans"))

@app.route("/add_transaction_page")
def add_transaction_page():
    if 'user_id' not in session:
        flash("Please login first", "error")
        return redirect(url_for("login"))

    merchants = db.tables["merchants"].rows
    customers = db.tables["customers"].rows
    return render_template("add_transaction.html", merchants=merchants, customers=customers)

@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    if 'user_id' not in session:
        flash("Please login first", "error")
        return redirect(url_for("login"))

    tid = str(random.randint(100000, 999999))
    merchant_id = request.form["merchant_id"]
    customer_id = request.form["customer_id"]

    try:
        amount = float(request.form["amount"])
        if amount <= 0:
            flash("Amount must be positive", "error")
            return redirect(url_for("add_transaction_page"))
    except:
        flash("Invalid amount", "error")
        return redirect(url_for("add_transaction_page"))

    status = request.form.get("status", "pending")
    if status not in ["pending", "complete", "failed"]:
        flash("Invalid status", "error")
        return redirect(url_for("add_transaction_page"))

    fraud_flag = "Yes" if amount > 10000 else "No"

    transaction = {
        "id": tid,
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "amount": amount,
        "status": status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fraud_flag": fraud_flag,
        "due_date": None
    }

    try:
        db.insert("transactions", transaction)
        db._save_data()
        flash("Transaction added successfully!", "success")
    except ValueError as e:
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for("user_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)