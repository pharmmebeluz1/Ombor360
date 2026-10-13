from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="employee")
    monthly_salary = db.Column(db.Float, nullable=False, default=0)
    telegram_chat_id = db.Column(db.String(64), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def can(self, *roles):
        return self.role in roles


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def free_quantity(self):
        return max(self.quantity - self.reserved_quantity, 0)


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movement_no = db.Column(db.String(30), unique=True, nullable=False)
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

    product = db.relationship("Product")
    created_by = db.relationship("User")


class CashRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_no = db.Column(db.String(30), unique=True, nullable=False)
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

    employee = db.relationship("User", foreign_keys=[employee_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])
    cashier_by = db.relationship("User", foreign_keys=[cashier_by_id])


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employee = db.relationship("User", foreign_keys=[employee_id])


class Revenue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PayrollPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    month_key = db.Column(db.String(7), nullable=False)  # YYYY-MM
    gross_salary = db.Column(db.Float, nullable=False)
    advances = db.Column(db.Float, nullable=False, default=0)
    paid_amount = db.Column(db.Float, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employee = db.relationship("User", foreign_keys=[employee_id])


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(40), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
