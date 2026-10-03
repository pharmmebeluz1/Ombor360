import os
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import AuditLog, CashRequest, Expense, PayrollPayment, Product, Revenue, StockMovement, User, db

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///ombor360.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco


def audit(action, entity, entity_id=None, details=None):
    db.session.add(AuditLog(
        user_id=current_user.id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id else None,
        details=details,
    ))


def next_no(prefix, model):
    today = datetime.now().strftime("%Y%m%d")
    count = model.query.filter(model.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).count() + 1
    return f"{prefix}-{today}-{count:04d}"


def money(v):
    return f"{v:,.0f}".replace(",", " ")


def month_range(month_key):
    year, month = map(int, month_key.split("-"))
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def seed_defaults():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add_all([
            User(full_name="Rahbar", username="admin", password_hash=generate_password_hash("admin123"), role="admin"),
            User(full_name="Omborchi", username="ombor", password_hash=generate_password_hash("1234"), role="warehouse"),
            User(full_name="Kassir", username="kassir", password_hash=generate_password_hash("1234"), role="cashier"),
            User(full_name="Buxgalter", username="buxgalter", password_hash=generate_password_hash("1234"), role="accountant"),
        ])
        db.session.commit()


app.jinja_env.filters["money"] = money

with app.app_context():
    seed_defaults()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"].strip()).first()
        if user and user.active and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Login yoki parol noto‘g‘ri", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    products = Product.query.order_by(Product.name).all()
    inventory_cost = sum(p.quantity * p.cost_price for p in products)
    inventory_sale = sum(p.quantity * p.sale_price for p in products)
    low_stock = [p for p in products if p.quantity <= p.min_quantity]
    total_revenue = db.session.query(db.func.coalesce(db.func.sum(Revenue.amount), 0)).scalar() or 0
    total_expense = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).scalar() or 0
    profit = total_revenue - total_expense
    recent = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(10).all()
    pending_cash = CashRequest.query.filter(CashRequest.status.in_(["PENDING", "APPROVED", "PAID"])).count()
    return render_template("dashboard.html", products=products, inventory_cost=inventory_cost,
                           inventory_sale=inventory_sale, low_stock=low_stock, total_revenue=total_revenue,
                           total_expense=total_expense, profit=profit, recent=recent, pending_cash=pending_cash)


@app.route("/products", methods=["GET", "POST"])
@role_required("admin", "manager", "warehouse")
def products():
    if request.method == "POST":
        p = Product(
            name=request.form["name"].strip(),
            category=request.form.get("category", "Boshqa").strip(),
            unit=request.form.get("unit", "dona").strip(),
            sku=request.form.get("sku") or None,
            min_quantity=float(request.form.get("min_quantity") or 0),
            cost_price=float(request.form.get("cost_price") or 0),
            sale_price=float(request.form.get("sale_price") or 0),
            location=request.form.get("location") or None,
        )
        db.session.add(p)
        db.session.flush()
        audit("CREATE", "Product", p.id, p.name)
        db.session.commit()
        flash("Mahsulot qo‘shildi", "success")
        return redirect(url_for("products"))
    return render_template("products.html", products=Product.query.order_by(Product.name).all())


@app.route("/movement/<kind>", methods=["GET", "POST"])
@role_required("admin", "manager", "warehouse")
def movement(kind):
    kind = kind.upper()
    if kind not in {"IN", "OUT", "RETURN"}:
        abort(404)
    products = Product.query.order_by(Product.name).all()
    if request.method == "POST":
        p = db.session.get(Product, int(request.form["product_id"]))
        qty = float(request.form["quantity"])
        if qty <= 0:
            flash("Miqdor 0 dan katta bo‘lishi kerak", "danger")
            return redirect(request.url)
        if kind == "OUT" and qty > p.free_quantity:
            flash(f"Yetarli erkin qoldiq yo‘q. Erkin: {p.free_quantity:g} {p.unit}", "danger")
            return redirect(request.url)
        if kind in {"IN", "RETURN"}:
            p.quantity += qty
        else:
            p.quantity -= qty
        unit_price = float(request.form.get("unit_price") or (p.cost_price if kind == "IN" else p.sale_price))
        if kind == "IN" and unit_price > 0:
            p.cost_price = unit_price
        m = StockMovement(
            movement_no=next_no("KR" if kind in {"IN", "RETURN"} else "CH", StockMovement),
            movement_type=kind,
            product_id=p.id,
            quantity=qty,
            unit_price=unit_price,
            supplier_or_destination=request.form.get("supplier_or_destination") or None,
            vehicle_model=request.form.get("vehicle_model") or None,
            vehicle_plate=request.form.get("vehicle_plate") or None,
            driver_name=request.form.get("driver_name") or None,
            given_by=request.form.get("given_by") or None,
            received_by=request.form.get("received_by") or None,
            order_no=request.form.get("order_no") or None,
            note=request.form.get("note") or None,
            camera_url=request.form.get("camera_url") or None,
            created_by_id=current_user.id,
        )
        db.session.add(m)
        db.session.flush()
        audit("CREATE", "StockMovement", m.id, f"{kind} {p.name} {qty} {p.unit}")
        db.session.commit()
        flash("Operatsiya saqlandi", "success")
        return redirect(url_for("movements"))
    return render_template("movement_form.html", kind=kind, products=products)


@app.route("/movements")
@login_required
def movements():
    rows = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(300).all()
    return render_template("movements.html", rows=rows)


@app.route("/cash", methods=["GET", "POST"])
@login_required
def cash_requests():
    if request.method == "POST":
        cr = CashRequest(
            request_no=next_no("PS", CashRequest),
            employee_id=current_user.id,
            amount=float(request.form["amount"]),
            category=request.form.get("category", "Avans"),
            reason=request.form["reason"].strip(),
        )
        db.session.add(cr)
        db.session.flush()
        audit("CREATE", "CashRequest", cr.id, f"{cr.amount} {cr.category}")
        db.session.commit()
        flash("Pul so‘rovi rahbarga yuborildi", "success")
        return redirect(url_for("cash_requests"))
    if current_user.can("admin", "manager", "cashier", "accountant"):
        rows = CashRequest.query.order_by(CashRequest.created_at.desc()).all()
    else:
        rows = CashRequest.query.filter_by(employee_id=current_user.id).order_by(CashRequest.created_at.desc()).all()
    return render_template("cash.html", rows=rows)


@app.post("/cash/<int:rid>/approve")
@role_required("admin", "manager")
def approve_cash(rid):
    cr = db.session.get(CashRequest, rid) or abort(404)
    if cr.status != "PENDING":
        abort(400)
    cr.status = "APPROVED"
    cr.approved_by_id = current_user.id
    cr.approved_at = datetime.utcnow()
    audit("APPROVE", "CashRequest", cr.id)
    db.session.commit()
    flash("So‘rov tasdiqlandi", "success")
    return redirect(url_for("cash_requests"))


@app.post("/cash/<int:rid>/reject")
@role_required("admin", "manager")
def reject_cash(rid):
    cr = db.session.get(CashRequest, rid) or abort(404)
    if cr.status != "PENDING":
        abort(400)
    cr.status = "REJECTED"
    cr.approved_by_id = current_user.id
    cr.approved_at = datetime.utcnow()
    audit("REJECT", "CashRequest", cr.id)
    db.session.commit()
    flash("So‘rov rad etildi", "warning")
    return redirect(url_for("cash_requests"))


@app.post("/cash/<int:rid>/pay")
@role_required("admin", "cashier")
def pay_cash(rid):
    cr = db.session.get(CashRequest, rid) or abort(404)
    if cr.status != "APPROVED":
        abort(400)
    cr.status = "PAID"
    cr.cashier_by_id = current_user.id
    cr.paid_at = datetime.utcnow()
    audit("PAY", "CashRequest", cr.id)
    db.session.commit()
    flash("Pul berildi. Xodim tasdig‘i kutilmoqda", "success")
    return redirect(url_for("cash_requests"))


@app.post("/cash/<int:rid>/received")
@login_required
def receive_cash(rid):
    cr = db.session.get(CashRequest, rid) or abort(404)
    if cr.employee_id != current_user.id and not current_user.can("admin"):
        abort(403)
    if cr.status != "PAID":
        abort(400)
    cr.status = "RECEIVED"
    cr.received_at = datetime.utcnow()
    if cr.category != "Avans":
        db.session.add(Expense(category=cr.category, amount=cr.amount, note=f"{cr.request_no}: {cr.reason}",
                               employee_id=cr.employee_id, created_by_id=current_user.id))
    audit("RECEIVED", "CashRequest", cr.id)
    db.session.commit()
    flash("Pulni olganingiz tasdiqlandi", "success")
    return redirect(url_for("cash_requests"))


@app.route("/finance", methods=["GET", "POST"])
@role_required("admin", "manager", "accountant")
def finance():
    if request.method == "POST":
        kind = request.form["kind"]
        amount = float(request.form["amount"])
        if kind == "revenue":
            row = Revenue(source=request.form.get("category") or "Savdo", amount=amount,
                          note=request.form.get("note"), created_by_id=current_user.id)
            db.session.add(row)
            db.session.flush()
            audit("CREATE", "Revenue", row.id)
        else:
            row = Expense(category=request.form.get("category") or "Boshqa", amount=amount,
                          note=request.form.get("note"), created_by_id=current_user.id)
            db.session.add(row)
            db.session.flush()
            audit("CREATE", "Expense", row.id)
        db.session.commit()
        flash("Moliyaviy yozuv qo‘shildi", "success")
        return redirect(url_for("finance"))
    revenues = Revenue.query.order_by(Revenue.created_at.desc()).limit(100).all()
    expenses = Expense.query.order_by(Expense.created_at.desc()).limit(100).all()
    return render_template("finance.html", revenues=revenues, expenses=expenses)


@app.route("/employees", methods=["GET", "POST"])
@role_required("admin", "manager", "accountant")
def employees():
    if request.method == "POST":
        u = User(
            full_name=request.form["full_name"].strip(),
            username=request.form["username"].strip(),
            password_hash=generate_password_hash(request.form.get("password") or "1234"),
            role=request.form.get("role", "employee"),
            monthly_salary=float(request.form.get("monthly_salary") or 0),
        )
        db.session.add(u)
        db.session.flush()
        audit("CREATE", "User", u.id, u.full_name)
        db.session.commit()
        flash("Xodim qo‘shildi", "success")
        return redirect(url_for("employees"))
    users = User.query.order_by(User.full_name).all()
    return render_template("employees.html", users=users)


@app.route("/payroll", methods=["GET", "POST"])
@role_required("admin", "manager", "accountant", "cashier")
def payroll():
    month_key = request.args.get("month") or datetime.now().strftime("%Y-%m")
    users = User.query.filter(User.active == True, User.role != "admin").order_by(User.full_name).all()
    rows = []
    start, end = month_range(month_key)
    for u in users:
        advances = db.session.query(db.func.coalesce(db.func.sum(CashRequest.amount), 0)).filter(
            CashRequest.employee_id == u.id,
            CashRequest.category == "Avans",
            CashRequest.status == "RECEIVED",
            CashRequest.received_at >= start,
            CashRequest.received_at < end,
        ).scalar() or 0
        paid = PayrollPayment.query.filter_by(employee_id=u.id, month_key=month_key).first()
        rows.append((u, float(advances), paid))
    return render_template("payroll.html", month_key=month_key, rows=rows)


@app.post("/payroll/<int:uid>/pay")
@role_required("admin", "manager", "accountant", "cashier")
def pay_salary(uid):
    u = db.session.get(User, uid) or abort(404)
    month_key = request.form["month_key"]
    existing = PayrollPayment.query.filter_by(employee_id=u.id, month_key=month_key).first()
    if existing:
        flash("Bu oy uchun oylik allaqachon yopilgan", "warning")
        return redirect(url_for("payroll", month=month_key))
    start, end = month_range(month_key)
    advances = db.session.query(db.func.coalesce(db.func.sum(CashRequest.amount), 0)).filter(
        CashRequest.employee_id == u.id,
        CashRequest.category == "Avans",
        CashRequest.status == "RECEIVED",
        CashRequest.received_at >= start,
        CashRequest.received_at < end,
    ).scalar() or 0
    pay_amount = max(float(u.monthly_salary) - float(advances), 0)
    p = PayrollPayment(employee_id=u.id, month_key=month_key, gross_salary=u.monthly_salary,
                       advances=advances, paid_amount=pay_amount, created_by_id=current_user.id)
    db.session.add(p)
    db.session.add(Expense(category="Oylik", amount=u.monthly_salary,
                           note=f"{month_key} {u.full_name}; avans {advances:g}; qo‘lga {pay_amount:g}",
                           employee_id=u.id, created_by_id=current_user.id))
    db.session.flush()
    audit("PAYROLL", "PayrollPayment", p.id, f"{u.full_name} {month_key}")
    db.session.commit()
    flash(f"{u.full_name}: {pay_amount:,.0f} so‘m berilishi kerak".replace(",", " "), "success")
    return redirect(url_for("payroll", month=month_key))


@app.route("/my-salary")
@login_required
def my_salary():
    month_key = request.args.get("month") or datetime.now().strftime("%Y-%m")
    start, end = month_range(month_key)
    advances = db.session.query(db.func.coalesce(db.func.sum(CashRequest.amount), 0)).filter(
        CashRequest.employee_id == current_user.id,
        CashRequest.category == "Avans",
        CashRequest.status == "RECEIVED",
        CashRequest.received_at >= start,
        CashRequest.received_at < end,
    ).scalar() or 0
    paid = PayrollPayment.query.filter_by(employee_id=current_user.id, month_key=month_key).first()
    return render_template("my_salary.html", month_key=month_key, advances=float(advances), paid=paid)


@app.route("/audit")
@role_required("admin", "manager")
def audit_view():
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(300).all()
    return render_template("audit.html", rows=rows)


@app.cli.command("init-db")
def init_db():
    seed_defaults()
    print("Ombor360 baza tayyor. Admin: admin / admin123")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
