import os
import re
import base64
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from barcode import Code128
from barcode.writer import SVGWriter
import qrcode
import qrcode.image.svg
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from models import (
    AuditLog,
    CashRequest,
    Company,
    Expense,
    PayrollPayment,
    Product,
    Revenue,
    StockMovement,
    User,
    db,
)

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")

database_url = os.getenv("DATABASE_URL", "sqlite:///ombor360.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def tashkent_now():
    return datetime.now(ZoneInfo("Asia/Tashkent"))


def current_company_id():
    if not current_user.is_authenticated:
        return None
    if current_user.role == "superadmin":
        return session.get("active_company_id")
    return current_user.company_id


def current_company():
    cid = current_company_id()
    return db.session.get(Company, int(cid)) if cid else None


def company_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_company_id():
            if current_user.role == "superadmin":
                return redirect(url_for("superadmin_dashboard"))
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role == "superadmin":
                if not current_company_id():
                    return redirect(url_for("superadmin_dashboard"))
                return fn(*args, **kwargs)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco


def superadmin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "superadmin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def tenant_query(model):
    cid = current_company_id()
    if not cid:
        abort(403)
    return model.query.filter(model.company_id == cid)


def tenant_get_or_404(model, row_id):
    row = tenant_query(model).filter(model.id == row_id).first()
    if not row:
        abort(404)
    return row


def company_user_or_404(user_id):
    cid = current_company_id()
    u = User.query.filter(User.id == user_id, User.company_id == cid).first()
    if not u:
        abort(404)
    return u


def audit(action, entity, entity_id=None, details=None):
    cid = current_company_id()
    if not cid:
        return
    db.session.add(AuditLog(
        company_id=cid,
        user_id=current_user.id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id else None,
        details=details,
    ))


def next_no(prefix, model):
    cid = current_company_id()
    company = current_company()
    today = datetime.now().strftime("%Y%m%d")
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = model.query.filter(model.company_id == cid, model.created_at >= start).count() + 1
    code = (company.code if company else f"C{cid}").upper()
    return f"{prefix}-{code}-{today}-{count:04d}"


def money(v):
    return f"{float(v or 0):,.0f}".replace(",", " ")


def qty(v):
    value = float(v or 0)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def barcode_svg_data_uri(code):
    try:
        buf = BytesIO()
        Code128(str(code), writer=SVGWriter()).write(
            buf,
            options={
                "module_width": 0.30,
                "module_height": 11.0,
                "quiet_zone": 1.5,
                "font_size": 7,
                "text_distance": 2.0,
                "write_text": True,
                "background": "white",
                "foreground": "black",
            },
        )
        return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def qr_svg_data_uri(code):
    try:
        qr = qrcode.QRCode(version=None, box_size=8, border=2)
        qr.add_data(str(code))
        qr.make(fit=True)
        image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        buf = BytesIO()
        image.save(buf)
        return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def ensure_columns():
    """v5/v7 bazani v8 multi-company sxemaga ma'lumotni o‘chirmasdan tayyorlaydi."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    quote = db.engine.dialect.identifier_preparer.quote

    product_additions = {
        "weight_kg": "FLOAT DEFAULT 0",
        "warehouse": "VARCHAR(120)",
        "row_code": "VARCHAR(40)",
        "shelf_code": "VARCHAR(40)",
        "expiry_date": "DATE",
    }
    if "product" in tables:
        existing = {c["name"] for c in inspector.get_columns("product")}
        for name, sql_type in product_additions.items():
            if name not in existing:
                db.session.execute(text(f"ALTER TABLE {quote('product')} ADD COLUMN {quote(name)} {sql_type}"))

    tenant_tables = ["user", "product", "stock_movement", "cash_request", "expense", "revenue", "payroll_payment", "audit_log"]
    inspector = inspect(db.engine)
    for table_name in tenant_tables:
        if table_name not in inspector.get_table_names():
            continue
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        if "company_id" not in existing:
            db.session.execute(text(f"ALTER TABLE {quote(table_name)} ADD COLUMN {quote('company_id')} INTEGER"))
    db.session.commit()


def make_company_code(name):
    raw = re.sub(r"[^A-Za-z0-9]", "", (name or "").upper())[:12] or "KORXONA"
    code = raw
    i = 2
    while Company.query.filter_by(code=code).first():
        code = f"{raw[:9]}{i}"
        i += 1
    return code


def seed_defaults():
    db.create_all()
    ensure_columns()

    default_company = Company.query.filter_by(code="MAIN").first()
    if not default_company:
        default_company = Company(
            name="Asosiy korxona",
            code="MAIN",
            plan_name="PRO",
            monthly_fee=0,
            subscription_start=tashkent_now().date(),
            subscription_end=tashkent_now().date() + timedelta(days=3650),
            active=True,
            note="Eski Ombor360 ma'lumotlari uchun avtomatik yaratilgan.",
        )
        db.session.add(default_company)
        db.session.flush()

    # Eski yozuvlarni bitta boshlang‘ich korxonaga biriktiramiz.
    quote = db.engine.dialect.identifier_preparer.quote
    inspector = inspect(db.engine)
    for table_name in ["user", "product", "stock_movement", "cash_request", "expense", "revenue", "payroll_payment", "audit_log"]:
        if table_name in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns(table_name)}
            if "company_id" in cols:
                db.session.execute(text(
                    f"UPDATE {quote(table_name)} SET {quote('company_id')} = :cid WHERE {quote('company_id')} IS NULL"
                ), {"cid": default_company.id})
    db.session.commit()

    if not User.query.filter_by(username="admin").first():
        db.session.add_all([
            User(company_id=default_company.id, full_name="Rahbar", username="admin", password_hash=generate_password_hash("admin123"), role="admin"),
            User(company_id=default_company.id, full_name="Omborchi", username="ombor", password_hash=generate_password_hash("1234"), role="warehouse"),
            User(company_id=default_company.id, full_name="Kassir", username="kassir", password_hash=generate_password_hash("1234"), role="cashier"),
            User(company_id=default_company.id, full_name="Buxgalter", username="buxgalter", password_hash=generate_password_hash("1234"), role="accountant"),
        ])

    super_username = os.getenv("SUPERADMIN_USERNAME", "superadmin").strip()
    super_password = os.getenv("SUPERADMIN_PASSWORD", "admin360").strip()
    sa = User.query.filter_by(username=super_username).first()
    if not sa:
        db.session.add(User(
            company_id=None,
            full_name="Ombor360 Super Admin",
            username=super_username,
            password_hash=generate_password_hash(super_password),
            role="superadmin",
            active=True,
        ))
    elif sa.role == "superadmin":
        sa.company_id = None
    db.session.commit()


app.jinja_env.filters["money"] = money
app.jinja_env.filters["qty"] = qty

with app.app_context():
    seed_defaults()


@app.before_request
def enforce_company_subscription():
    if not current_user.is_authenticated:
        return None
    endpoint = request.endpoint or ""
    if endpoint == "static" or endpoint in {"logout", "subscription_expired"} or endpoint.startswith("superadmin"):
        return None
    if current_user.role == "superadmin":
        if not session.get("active_company_id"):
            return redirect(url_for("superadmin_dashboard"))
        return None
    company = current_user.company
    if not company:
        return redirect(url_for("subscription_expired"))
    if not company.active or (company.subscription_end and company.subscription_end < tashkent_now().date()):
        return redirect(url_for("subscription_expired"))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("superadmin_dashboard" if current_user.role == "superadmin" else "dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"].strip()).first()
        if user and user.active and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            if user.role == "superadmin":
                session.pop("active_company_id", None)
                return redirect(url_for("superadmin_dashboard"))
            return redirect(url_for("dashboard"))
        flash("Login yoki parol noto‘g‘ri", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("active_company_id", None)
    logout_user()
    return redirect(url_for("login"))


@app.route("/subscription-expired")
@login_required
def subscription_expired():
    company = current_user.company if current_user.role != "superadmin" else current_company()
    if company and company.active and (not company.subscription_end or company.subscription_end >= tashkent_now().date()):
        return redirect(url_for("dashboard"))
    return render_template("subscription_expired.html", company=company)


@app.context_processor
def inject_layout_context():
    now = tashkent_now()
    weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    role_names = {
        "superadmin": "Super Admin",
        "admin": "admin",
        "manager": "rahbar",
        "warehouse": "omborchi",
        "cashier": "kassir",
        "accountant": "buxgalter",
        "employee": "xodim",
    }
    company = None
    effective_role = ""
    pending = 0
    subscription_days_left = None
    try:
        if current_user.is_authenticated:
            company = current_company()
            effective_role = "admin" if current_user.role == "superadmin" and company else current_user.role
            if company and company.subscription_end:
                subscription_days_left = (company.subscription_end - now.date()).days
            if company:
                pending = CashRequest.query.filter_by(company_id=company.id, status="PENDING").count()
    except Exception:
        pending = 0
    return {
        "today_text": now.strftime("%d.%m.%Y"),
        "weekday_text": weekdays[now.weekday()],
        "role_label": role_names.get(getattr(current_user, "role", ""), getattr(current_user, "role", "")),
        "effective_role": effective_role,
        "active_company": company,
        "subscription_days_left": subscription_days_left,
        "nav_pending_cash": pending,
    }


# ---------------- SUPER ADMIN / ABONENTLAR ----------------

@app.route("/superadmin")
@superadmin_required
def superadmin_dashboard():
    companies = Company.query.order_by(Company.created_at.desc()).all()
    today = tashkent_now().date()
    company_rows = []
    for c in companies:
        admin_user = User.query.filter_by(company_id=c.id, role="admin").order_by(User.id).first()
        users_count = User.query.filter_by(company_id=c.id, active=True).count()
        products_count = Product.query.filter_by(company_id=c.id).count()
        days_left = (c.subscription_end - today).days if c.subscription_end else None
        company_rows.append({
            "company": c,
            "admin_user": admin_user,
            "users_count": users_count,
            "products_count": products_count,
            "days_left": days_left,
        })
    active_count = sum(1 for c in companies if c.active and (not c.subscription_end or c.subscription_end >= today))
    expired_count = len(companies) - active_count
    monthly_total = sum(float(c.monthly_fee or 0) for c in companies if c.active and (not c.subscription_end or c.subscription_end >= today))
    return render_template(
        "superadmin.html",
        company_rows=company_rows,
        total_companies=len(companies),
        active_count=active_count,
        expired_count=expired_count,
        monthly_total=monthly_total,
        today=today,
    )


@app.post("/superadmin/company/create")
@superadmin_required
def superadmin_company_create():
    name = (request.form.get("name") or "").strip()
    admin_username = (request.form.get("admin_username") or "").strip()
    admin_password = request.form.get("admin_password") or "1234"
    if not name or not admin_username:
        flash("Korxona nomi va admin loginini kiriting", "danger")
        return redirect(url_for("superadmin_dashboard"))
    if User.query.filter_by(username=admin_username).first():
        flash("Bu login oldin ishlatilgan. Boshqa login tanlang.", "danger")
        return redirect(url_for("superadmin_dashboard"))

    code = (request.form.get("code") or "").strip().upper()
    code = re.sub(r"[^A-Z0-9]", "", code)[:12] or make_company_code(name)
    if Company.query.filter_by(code=code).first():
        code = make_company_code(name)
    days = max(1, int(request.form.get("subscription_days") or 30))
    start = tashkent_now().date()
    company = Company(
        name=name,
        code=code,
        phone=(request.form.get("phone") or "").strip() or None,
        plan_name=(request.form.get("plan_name") or "START").strip().upper(),
        monthly_fee=float(request.form.get("monthly_fee") or 10),
        subscription_start=start,
        subscription_end=start + timedelta(days=days),
        active=True,
        note=(request.form.get("note") or "").strip() or None,
    )
    db.session.add(company)
    db.session.flush()
    db.session.add(User(
        company_id=company.id,
        full_name=(request.form.get("admin_name") or "Rahbar").strip(),
        username=admin_username,
        password_hash=generate_password_hash(admin_password),
        role="admin",
        active=True,
    ))
    db.session.commit()
    flash(f"{company.name} yaratildi. Admin login: {admin_username}", "success")
    return redirect(url_for("superadmin_dashboard"))


@app.post("/superadmin/company/<int:company_id>/enter")
@superadmin_required
def superadmin_company_enter(company_id):
    company = db.session.get(Company, company_id) or abort(404)
    session["active_company_id"] = company.id
    flash(f"{company.name} kabinetiga kirdingiz", "success")
    return redirect(url_for("dashboard"))


@app.get("/superadmin/leave-company")
@superadmin_required
def superadmin_leave_company():
    session.pop("active_company_id", None)
    return redirect(url_for("superadmin_dashboard"))


@app.post("/superadmin/company/<int:company_id>/extend")
@superadmin_required
def superadmin_company_extend(company_id):
    company = db.session.get(Company, company_id) or abort(404)
    days = max(1, int(request.form.get("days") or 30))
    today = tashkent_now().date()
    base = company.subscription_end if company.subscription_end and company.subscription_end >= today else today
    company.subscription_end = base + timedelta(days=days)
    if not company.subscription_start:
        company.subscription_start = today
    company.active = True
    if request.form.get("monthly_fee") not in (None, ""):
        company.monthly_fee = float(request.form.get("monthly_fee") or 0)
    db.session.commit()
    flash(f"{company.name}: abonent {days} kunga uzaytirildi", "success")
    return redirect(url_for("superadmin_dashboard"))


@app.post("/superadmin/company/<int:company_id>/toggle")
@superadmin_required
def superadmin_company_toggle(company_id):
    company = db.session.get(Company, company_id) or abort(404)
    company.active = not company.active
    db.session.commit()
    flash(f"{company.name}: {'faollashtirildi' if company.active else 'vaqtincha to‘xtatildi'}", "warning" if not company.active else "success")
    return redirect(url_for("superadmin_dashboard"))


@app.post("/superadmin/company/<int:company_id>/update")
@superadmin_required
def superadmin_company_update(company_id):
    company = db.session.get(Company, company_id) or abort(404)
    company.plan_name = (request.form.get("plan_name") or company.plan_name).strip().upper()
    company.monthly_fee = float(request.form.get("monthly_fee") or company.monthly_fee or 0)
    company.phone = (request.form.get("phone") or "").strip() or None
    company.note = (request.form.get("note") or "").strip() or None
    db.session.commit()
    flash("Abonent ma'lumotlari yangilandi", "success")
    return redirect(url_for("superadmin_dashboard"))


@app.post("/superadmin/company/<int:company_id>/reset-password")
@superadmin_required
def superadmin_reset_password(company_id):
    company = db.session.get(Company, company_id) or abort(404)
    user = User.query.filter_by(company_id=company.id, role="admin").order_by(User.id).first()
    if not user:
        flash("Bu korxonada admin topilmadi", "danger")
        return redirect(url_for("superadmin_dashboard"))
    new_password = (request.form.get("new_password") or "").strip()
    if len(new_password) < 4:
        flash("Yangi parol kamida 4 ta belgidan iborat bo‘lsin", "danger")
        return redirect(url_for("superadmin_dashboard"))
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash(f"{company.name} admin paroli yangilandi", "success")
    return redirect(url_for("superadmin_dashboard"))


# ---------------- KORXONA KABINETI ----------------

@app.route("/")
@company_required
def dashboard():
    cid = current_company_id()
    products = Product.query.filter_by(company_id=cid).order_by(Product.name).all()
    inventory_cost = sum(float(p.quantity or 0) * float(p.cost_price or 0) for p in products)
    inventory_sale = sum(float(p.quantity or 0) * float(p.sale_price or 0) for p in products)
    low_stock = sorted([p for p in products if p.quantity <= p.min_quantity], key=lambda p: (p.quantity - p.min_quantity))
    total_revenue = float(db.session.query(db.func.coalesce(db.func.sum(Revenue.amount), 0)).filter(Revenue.company_id == cid).scalar() or 0)
    total_expense = float(db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).filter(Expense.company_id == cid).scalar() or 0)
    profit = total_revenue - total_expense
    recent = StockMovement.query.filter_by(company_id=cid, cancelled=False).order_by(StockMovement.created_at.desc()).limit(10).all()

    day_start, day_end = tashkent_day_utc_range()
    today_rows = StockMovement.query.filter(
        StockMovement.company_id == cid,
        StockMovement.cancelled == False,
        StockMovement.created_at >= day_start,
        StockMovement.created_at < day_end,
    ).all()
    today_in = [m for m in today_rows if m.movement_type in {"IN", "RETURN"}]
    today_out = [m for m in today_rows if m.movement_type == "OUT"]
    today_in_value = sum(float(m.quantity or 0) * float(m.unit_price or 0) for m in today_in)
    today_out_value = sum(float(m.quantity or 0) * float(m.unit_price or 0) for m in today_out)

    now = tashkent_now()
    chart_labels, chart_in, chart_out = [], [], []
    month_names = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
    for offset in range(-5, 1):
        y, mo = shift_month(now.year, now.month, offset)
        ey, em = shift_month(y, mo, 1)
        start_local = datetime(y, mo, 1, tzinfo=ZoneInfo("Asia/Tashkent"))
        end_local = datetime(ey, em, 1, tzinfo=ZoneInfo("Asia/Tashkent"))
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
        rows = StockMovement.query.filter(
            StockMovement.company_id == cid,
            StockMovement.cancelled == False,
            StockMovement.created_at >= start_utc,
            StockMovement.created_at < end_utc,
        ).all()
        chart_labels.append(month_names[mo - 1])
        chart_in.append(round(sum(float(m.quantity or 0) * float(m.unit_price or 0) for m in rows if m.movement_type in {"IN", "RETURN"}), 2))
        chart_out.append(round(sum(float(m.quantity or 0) * float(m.unit_price or 0) for m in rows if m.movement_type == "OUT"), 2))

    incoming_rows = StockMovement.query.filter(
        StockMovement.company_id == cid,
        StockMovement.cancelled == False,
        StockMovement.movement_type.in_(["IN", "RETURN"]),
    ).all()
    incoming_map = {}
    for m in incoming_rows:
        d = incoming_map.setdefault(m.product_id, {"name": m.product.name, "unit": m.product.unit, "quantity": 0.0})
        d["quantity"] += float(m.quantity or 0)
    top_raw = sorted(incoming_map.values(), key=lambda x: x["quantity"], reverse=True)[:5]
    top_max = max([x["quantity"] for x in top_raw], default=1)
    top_incoming = [{**x, "percent": max(8, round(x["quantity"] / top_max * 100))} for x in top_raw]

    cash_preview = CashRequest.query.filter_by(company_id=cid).order_by(CashRequest.created_at.desc()).limit(3).all()
    active_employees = User.query.filter_by(company_id=cid, active=True).count()
    total_quantity = sum(float(p.quantity or 0) for p in products)
    return render_template(
        "dashboard.html",
        products=products,
        inventory_cost=inventory_cost,
        inventory_sale=inventory_sale,
        low_stock=low_stock,
        total_revenue=total_revenue,
        total_expense=total_expense,
        profit=profit,
        recent=recent,
        today_in_value=today_in_value,
        today_out_value=today_out_value,
        today_in_count=len(today_in),
        today_out_count=len(today_out),
        active_employees=active_employees,
        chart_labels=chart_labels,
        chart_in=chart_in,
        chart_out=chart_out,
        top_incoming=top_incoming,
        cash_preview=cash_preview,
        total_product_types=len(products),
        total_quantity=total_quantity,
    )


def tashkent_day_utc_range():
    now_local = tashkent_now()
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def shift_month(year, month, offset):
    n = year * 12 + (month - 1) + offset
    return n // 12, n % 12 + 1


def month_range(month_key):
    year, month = map(int, month_key.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


@app.route("/products", methods=["GET", "POST"])
@role_required("admin", "manager", "warehouse")
def products():
    cid = current_company_id()
    company = current_company()
    if request.method == "POST":
        raw_sku = (request.form.get("sku") or "").strip() or None
        if raw_sku and Product.query.filter_by(company_id=cid, sku=raw_sku).first():
            flash("Bu barcode/SKU shu korxonada oldin boshqa mahsulotga biriktirilgan", "danger")
            return redirect(url_for("products"))
        warehouse = (request.form.get("warehouse") or "").strip() or None
        row_code = (request.form.get("row_code") or "").strip() or None
        shelf_code = (request.form.get("shelf_code") or "").strip() or None
        location_parts = [x for x in [warehouse, f"Qator {row_code}" if row_code else None, f"Polka {shelf_code}" if shelf_code else None] if x]
        p = Product(
            company_id=cid,
            name=request.form["name"].strip(),
            category=request.form.get("category", "Boshqa").strip(),
            unit=request.form.get("unit", "dona").strip(),
            sku=raw_sku,
            min_quantity=float(request.form.get("min_quantity") or 0),
            cost_price=float(request.form.get("cost_price") or 0),
            sale_price=float(request.form.get("sale_price") or 0),
            weight_kg=float(request.form.get("weight_kg") or 0),
            warehouse=warehouse,
            row_code=row_code,
            shelf_code=shelf_code,
            expiry_date=parse_date(request.form.get("expiry_date")),
            location=" → ".join(location_parts) or ((request.form.get("location") or "").strip() or None),
        )
        db.session.add(p)
        db.session.flush()
        if not p.sku:
            p.sku = f"{company.code}-OMB-{p.id:06d}"
        audit("CREATE", "Product", p.id, f"{p.name} | barcode: {p.sku}")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Bu barcode boshqa akkauntda ham ishlatilgan. Hozircha boshqa kod kiriting.", "danger")
            return redirect(url_for("products"))
        flash("Mahsulot qo‘shildi. QR-kod avtomatik yaratildi.", "success")
        return redirect(url_for("labels", ids=p.id, label_type="qr", created=1))
    q = (request.args.get("q") or "").strip()
    query = Product.query.filter(Product.company_id == cid)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Product.name.ilike(like),
            Product.sku.ilike(like),
            Product.category.ilike(like),
            Product.warehouse.ilike(like),
            Product.row_code.ilike(like),
            Product.shelf_code.ilike(like),
        ))
    return render_template("products.html", products=query.order_by(Product.name).all(), q=q)


@app.route("/labels")
@role_required("admin", "manager", "warehouse")
def labels():
    cid = current_company_id()
    ids_raw = (request.args.get("ids") or "").strip()
    copies_raw = (request.args.get("copies") or "1").strip()
    try:
        copies = max(1, min(int(copies_raw), 50))
    except ValueError:
        copies = 1
    query = Product.query.filter(Product.company_id == cid)
    selected_ids = []
    if ids_raw:
        for part in ids_raw.split(","):
            try:
                selected_ids.append(int(part.strip()))
            except (TypeError, ValueError):
                pass
        if selected_ids:
            query = query.filter(Product.id.in_(selected_ids))
    label_type = (request.args.get("label_type") or "qr").lower()
    if label_type not in {"qr", "barcode"}:
        label_type = "qr"
    products_rows = query.order_by(Product.name).all()
    label_rows = []
    for product in products_rows:
        code = product.sku or f"{current_company().code}-OMB-{product.id:06d}"
        barcode_uri = barcode_svg_data_uri(code)
        qr_uri = qr_svg_data_uri(code)
        for _ in range(copies):
            label_rows.append({"product": product, "code": code, "barcode_uri": barcode_uri, "qr_uri": qr_uri})
    return render_template(
        "labels.html",
        label_rows=label_rows,
        ids_raw=ids_raw,
        copies=copies,
        label_type=label_type,
        created=request.args.get("created") == "1",
        product_count=len(products_rows),
    )


@app.route("/scan", methods=["GET", "POST"])
@company_required
def scan_product():
    cid = current_company_id()
    code = (request.values.get("code") or "").strip()
    if code:
        product = Product.query.filter(Product.company_id == cid, db.func.lower(Product.sku) == code.lower()).first()
        if product:
            return redirect(url_for("product_card", product_id=product.id))
        flash(f"{code} kodi bilan mahsulot topilmadi", "danger")
        return redirect(url_for("scan_product"))
    return render_template("scan.html")


@app.route("/product/<int:product_id>")
@company_required
def product_card(product_id):
    product = tenant_get_or_404(Product, product_id)
    days_left = None
    expiry_status = None
    if product.expiry_date:
        days_left = (product.expiry_date - tashkent_now().date()).days
        if days_left < 0:
            expiry_status = "expired"
        elif days_left <= 7:
            expiry_status = "danger"
        elif days_left <= 30:
            expiry_status = "warning"
        else:
            expiry_status = "ok"
    return render_template(
        "product_card.html",
        product=product,
        days_left=days_left,
        expiry_status=expiry_status,
        qr_uri=qr_svg_data_uri(product.sku or f"{current_company().code}-OMB-{product.id:06d}"),
    )


@app.route("/movement/<kind>", methods=["GET", "POST"])
@role_required("admin", "manager", "warehouse")
def movement(kind):
    cid = current_company_id()
    kind = kind.upper()
    if kind not in {"IN", "OUT", "RETURN"}:
        abort(404)
    products_rows = Product.query.filter_by(company_id=cid).order_by(Product.name).all()
    if request.method == "POST":
        p = tenant_get_or_404(Product, int(request.form["product_id"]))
        qty_value = float(request.form["quantity"])
        if qty_value <= 0:
            flash("Miqdor 0 dan katta bo‘lishi kerak", "danger")
            return redirect(request.url)
        if kind == "OUT" and qty_value > p.free_quantity:
            flash(f"Yetarli erkin qoldiq yo‘q. Erkin: {p.free_quantity:g} {p.unit}", "danger")
            return redirect(request.url)
        if kind in {"IN", "RETURN"}:
            p.quantity += qty_value
        else:
            p.quantity -= qty_value
        unit_price = float(request.form.get("unit_price") or (p.cost_price if kind == "IN" else p.sale_price))
        if kind == "IN" and unit_price > 0:
            p.cost_price = unit_price
        m = StockMovement(
            company_id=cid,
            movement_no=next_no("KR" if kind in {"IN", "RETURN"} else "CH", StockMovement),
            movement_type=kind,
            product_id=p.id,
            quantity=qty_value,
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
        audit("CREATE", "StockMovement", m.id, f"{kind} {p.name} {qty_value} {p.unit}")
        db.session.commit()
        flash("Operatsiya saqlandi", "success")
        return redirect(url_for("movements"))
    preselected_id = request.args.get("product_id", type=int)
    if preselected_id and not Product.query.filter_by(id=preselected_id, company_id=cid).first():
        preselected_id = None
    return render_template("movement_form.html", kind=kind, products=products_rows, preselected_id=preselected_id)


@app.route("/movements")
@company_required
def movements():
    rows = StockMovement.query.filter_by(company_id=current_company_id()).order_by(StockMovement.created_at.desc()).limit(300).all()
    return render_template("movements.html", rows=rows)


@app.route("/cash", methods=["GET", "POST"])
@company_required
def cash_requests():
    cid = current_company_id()
    if request.method == "POST":
        if current_user.role == "superadmin":
            flash("Super Admin korxona xodimi nomidan pul so‘rovi yubormaydi", "warning")
            return redirect(url_for("cash_requests"))
        cr = CashRequest(
            company_id=cid,
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
    if current_user.role == "superadmin" or current_user.can("admin", "manager", "cashier", "accountant"):
        rows = CashRequest.query.filter_by(company_id=cid).order_by(CashRequest.created_at.desc()).all()
    else:
        rows = CashRequest.query.filter_by(company_id=cid, employee_id=current_user.id).order_by(CashRequest.created_at.desc()).all()
    return render_template("cash.html", rows=rows)


@app.post("/cash/<int:rid>/approve")
@role_required("admin", "manager")
def approve_cash(rid):
    cr = tenant_get_or_404(CashRequest, rid)
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
    cr = tenant_get_or_404(CashRequest, rid)
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
    cr = tenant_get_or_404(CashRequest, rid)
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
@company_required
def receive_cash(rid):
    cid = current_company_id()
    cr = tenant_get_or_404(CashRequest, rid)
    if cr.employee_id != current_user.id and current_user.role != "superadmin" and not current_user.can("admin"):
        abort(403)
    if cr.status != "PAID":
        abort(400)
    cr.status = "RECEIVED"
    cr.received_at = datetime.utcnow()
    if cr.category != "Avans":
        db.session.add(Expense(
            company_id=cid,
            category=cr.category,
            amount=cr.amount,
            note=f"{cr.request_no}: {cr.reason}",
            employee_id=cr.employee_id,
            created_by_id=current_user.id,
        ))
    audit("RECEIVED", "CashRequest", cr.id)
    db.session.commit()
    flash("Pulni olganingiz tasdiqlandi", "success")
    return redirect(url_for("cash_requests"))


@app.route("/finance", methods=["GET", "POST"])
@role_required("admin", "manager", "accountant")
def finance():
    cid = current_company_id()
    if request.method == "POST":
        kind = request.form["kind"]
        amount = float(request.form["amount"])
        if kind == "revenue":
            row = Revenue(
                company_id=cid,
                source=request.form.get("category") or "Savdo",
                amount=amount,
                note=request.form.get("note"),
                created_by_id=current_user.id,
            )
            db.session.add(row)
            db.session.flush()
            audit("CREATE", "Revenue", row.id)
        else:
            row = Expense(
                company_id=cid,
                category=request.form.get("category") or "Boshqa",
                amount=amount,
                note=request.form.get("note"),
                created_by_id=current_user.id,
            )
            db.session.add(row)
            db.session.flush()
            audit("CREATE", "Expense", row.id)
        db.session.commit()
        flash("Moliyaviy yozuv qo‘shildi", "success")
        return redirect(url_for("finance"))
    revenues = Revenue.query.filter_by(company_id=cid).order_by(Revenue.created_at.desc()).limit(100).all()
    expenses = Expense.query.filter_by(company_id=cid).order_by(Expense.created_at.desc()).limit(100).all()
    return render_template("finance.html", revenues=revenues, expenses=expenses)


@app.route("/employees", methods=["GET", "POST"])
@role_required("admin", "manager", "accountant")
def employees():
    cid = current_company_id()
    if request.method == "POST":
        username = request.form["username"].strip()
        if User.query.filter_by(username=username).first():
            flash("Bu login band. Boshqa login kiriting.", "danger")
            return redirect(url_for("employees"))
        u = User(
            company_id=cid,
            full_name=request.form["full_name"].strip(),
            username=username,
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
    users = User.query.filter_by(company_id=cid).order_by(User.full_name).all()
    return render_template("employees.html", users=users)


@app.route("/payroll", methods=["GET", "POST"])
@role_required("admin", "manager", "accountant", "cashier")
def payroll():
    cid = current_company_id()
    month_key = request.args.get("month") or datetime.now().strftime("%Y-%m")
    users = User.query.filter(User.company_id == cid, User.active == True, User.role != "admin").order_by(User.full_name).all()
    rows = []
    start, end = month_range(month_key)
    for u in users:
        advances = db.session.query(db.func.coalesce(db.func.sum(CashRequest.amount), 0)).filter(
            CashRequest.company_id == cid,
            CashRequest.employee_id == u.id,
            CashRequest.category == "Avans",
            CashRequest.status == "RECEIVED",
            CashRequest.received_at >= start,
            CashRequest.received_at < end,
        ).scalar() or 0
        paid = PayrollPayment.query.filter_by(company_id=cid, employee_id=u.id, month_key=month_key).first()
        rows.append((u, float(advances), paid))
    return render_template("payroll.html", month_key=month_key, rows=rows)


@app.post("/payroll/<int:uid>/pay")
@role_required("admin", "manager", "accountant", "cashier")
def pay_salary(uid):
    cid = current_company_id()
    u = company_user_or_404(uid)
    month_key = request.form["month_key"]
    existing = PayrollPayment.query.filter_by(company_id=cid, employee_id=u.id, month_key=month_key).first()
    if existing:
        flash("Bu oy uchun oylik allaqachon yopilgan", "warning")
        return redirect(url_for("payroll", month=month_key))
    start, end = month_range(month_key)
    advances = db.session.query(db.func.coalesce(db.func.sum(CashRequest.amount), 0)).filter(
        CashRequest.company_id == cid,
        CashRequest.employee_id == u.id,
        CashRequest.category == "Avans",
        CashRequest.status == "RECEIVED",
        CashRequest.received_at >= start,
        CashRequest.received_at < end,
    ).scalar() or 0
    pay_amount = max(float(u.monthly_salary) - float(advances), 0)
    p = PayrollPayment(
        company_id=cid,
        employee_id=u.id,
        month_key=month_key,
        gross_salary=u.monthly_salary,
        advances=advances,
        paid_amount=pay_amount,
        created_by_id=current_user.id,
    )
    db.session.add(p)
    db.session.add(Expense(
        company_id=cid,
        category="Oylik",
        amount=u.monthly_salary,
        note=f"{month_key} {u.full_name}; avans {advances:g}; qo‘lga {pay_amount:g}",
        employee_id=u.id,
        created_by_id=current_user.id,
    ))
    db.session.flush()
    audit("PAYROLL", "PayrollPayment", p.id, f"{u.full_name} {month_key}")
    db.session.commit()
    flash(f"{u.full_name}: {pay_amount:,.0f} so‘m berilishi kerak".replace(",", " "), "success")
    return redirect(url_for("payroll", month=month_key))


@app.route("/my-salary")
@company_required
def my_salary():
    if current_user.role == "superadmin":
        flash("Super Admin uchun oylik kabineti qo‘llanmaydi", "warning")
        return redirect(url_for("dashboard"))
    cid = current_company_id()
    month_key = request.args.get("month") or datetime.now().strftime("%Y-%m")
    start, end = month_range(month_key)
    advances = db.session.query(db.func.coalesce(db.func.sum(CashRequest.amount), 0)).filter(
        CashRequest.company_id == cid,
        CashRequest.employee_id == current_user.id,
        CashRequest.category == "Avans",
        CashRequest.status == "RECEIVED",
        CashRequest.received_at >= start,
        CashRequest.received_at < end,
    ).scalar() or 0
    paid = PayrollPayment.query.filter_by(company_id=cid, employee_id=current_user.id, month_key=month_key).first()
    return render_template("my_salary.html", month_key=month_key, advances=float(advances), paid=paid)


@app.route("/audit")
@role_required("admin", "manager")
def audit_view():
    rows = AuditLog.query.filter_by(company_id=current_company_id()).order_by(AuditLog.created_at.desc()).limit(300).all()
    return render_template("audit.html", rows=rows)


@app.route("/reports")
@role_required("admin", "manager")
def reports():
    cid = current_company_id()
    products_rows = Product.query.filter_by(company_id=cid).all()
    inventory_cost = sum(float(p.quantity or 0) * float(p.cost_price or 0) for p in products_rows)
    total_revenue = float(db.session.query(db.func.coalesce(db.func.sum(Revenue.amount), 0)).filter(Revenue.company_id == cid).scalar() or 0)
    total_expense = float(db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).filter(Expense.company_id == cid).scalar() or 0)
    low_count = sum(1 for p in products_rows if p.quantity <= p.min_quantity)
    movement_count = StockMovement.query.filter_by(company_id=cid, cancelled=False).count()
    return render_template(
        "reports.html",
        total_revenue=total_revenue,
        total_expense=total_expense,
        product_count=len(products_rows),
        inventory_cost=inventory_cost,
        low_count=low_count,
        movement_count=movement_count,
    )


@app.route("/settings")
@role_required("admin", "manager")
def settings_view():
    database_kind = "PostgreSQL" if "postgresql" in str(app.config.get("SQLALCHEMY_DATABASE_URI", "")) else "SQLite"
    return render_template("settings.html", database_kind=database_kind, company=current_company())


@app.cli.command("init-db")
def init_db():
    seed_defaults()
    print("Ombor360 v8 baza tayyor.")
    print("Super Admin: SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD (.env orqali)")


if __name__ == "__main__":
    with app.app_context():
        seed_defaults()
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
