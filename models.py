from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    plan_name = db.Column(db.String(40), nullable=False, default="START")
    monthly_fee = db.Column(db.Float, nullable=False, default=10)
    subscription_start = db.Column(db.Date, nullable=True)
    subscription_end = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def subscription_ok(self):
        if not self.active:
            return False
        if not self.subscription_end:
            return True
        return self.subscription_end >= datetime.utcnow().date()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="employee")
    monthly_salary = db.Column(db.Float, nullable=False, default=0)
    telegram_chat_id = db.Column(db.String(64), nullable=True)
    active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    last_device = db.Column(db.String(180), nullable=True)
    last_page = db.Column(db.String(180), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship("Company")

    def can(self, *roles):
        return self.role == "superadmin" or self.role in roles


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    name = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Boshqa")
    unit = db.Column(db.String(20), nullable=False, default="dona")
    sku = db.Column(db.String(80), unique=True, nullable=True)
    quantity = db.Column(db.Float, nullable=False, default=0)
    reserved_quantity = db.Column(db.Float, nullable=False, default=0)
    min_quantity = db.Column(db.Float, nullable=False, default=0)
    cost_price = db.Column(db.Float, nullable=False, default=0)
    sale_price = db.Column(db.Float, nullable=False, default=0)
    location = db.Column(db.String(120), nullable=True)
    weight_kg = db.Column(db.Float, nullable=False, default=0)
    warehouse = db.Column(db.String(120), nullable=True)
    row_code = db.Column(db.String(40), nullable=True)
    shelf_code = db.Column(db.String(40), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship("Company")

    @property
    def free_quantity(self):
        return max(self.quantity - self.reserved_quantity, 0)


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    movement_no = db.Column(db.String(50), unique=True, nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # IN / OUT / RETURN / ADJUST
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False, default=0)
    supplier_or_destination = db.Column(db.String(160), nullable=True)
    vehicle_model = db.Column(db.String(100), nullable=True)
    vehicle_plate = db.Column(db.String(40), nullable=True)
    driver_name = db.Column(db.String(120), nullable=True)
    given_by = db.Column(db.String(120), nullable=True)
    received_by = db.Column(db.String(120), nullable=True)
    order_no = db.Column(db.String(80), nullable=True)
    note = db.Column(db.Text, nullable=True)
    camera_url = db.Column(db.String(500), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled = db.Column(db.Boolean, default=False)

    company = db.relationship("Company")
    product = db.relationship("Product")
    created_by = db.relationship("User")


class CashRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    request_no = db.Column(db.String(50), unique=True, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(40), nullable=False, default="Avans")
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="PENDING")
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    cashier_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    received_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship("Company")
    employee = db.relationship("User", foreign_keys=[employee_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])
    cashier_by = db.relationship("User", foreign_keys=[cashier_by_id])


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    category = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company = db.relationship("Company")
    employee = db.relationship("User", foreign_keys=[employee_id])


class Revenue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    source = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company = db.relationship("Company")


class PayrollPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    month_key = db.Column(db.String(7), nullable=False)  # YYYY-MM
    gross_salary = db.Column(db.Float, nullable=False)
    advances = db.Column(db.Float, nullable=False, default=0)
    paid_amount = db.Column(db.Float, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company = db.relationship("Company")
    employee = db.relationship("User", foreign_keys=[employee_id])


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(40), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company = db.relationship("Company")


class SupportEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    level = db.Column(db.String(20), nullable=False, default="INFO")
    event_type = db.Column(db.String(40), nullable=False, default="SYSTEM")
    path = db.Column(db.String(180), nullable=True)
    message = db.Column(db.String(500), nullable=False)
    details = db.Column(db.Text, nullable=True)
    device = db.Column(db.String(180), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    company = db.relationship("Company")
    user = db.relationship("User")
