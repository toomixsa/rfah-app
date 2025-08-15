# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import (
    Flask, request, jsonify, session, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------------
# إعدادات المسارات
# -------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(BASE_DIR, "static"))  # /app/src/static داخل الصورة

# -------------------------------------------------
# إنشاء التطبيق وتهيئة الإعدادات
# -------------------------------------------------
app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    static_url_path=""   # يسمح بـ /assets/... مباشرة من static
)

# سرّ الجلسة
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# DB URI
db_uri = (
    os.getenv("SQLALCHEMY_DATABASE_URI") or
    os.getenv("DATABASE_URL") or
    f"sqlite:///{os.getenv('INSTANCE_DIR', '/app/instance')}/app.db"
)
app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# إعدادات الكوكي للجلسة
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True  # على كوييب عبر HTTPS

# CORS (ليس ضروريًا مع نفس الأصل، لكن لن يحتكّ)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# DB
db = SQLAlchemy(app)

# -------------------------------------------------
# نموذج المستخدم
# -------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def to_safe_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name or "",
            "is_active": self.is_active,
            "is_admin": self.is_admin,
        }

# -------------------------------------------------
# تهيئة الجداول و Seed حساب الأدمن
# -------------------------------------------------
def seed_admin() -> None:
    """ينشئ حساب مدير لو غير موجود."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    existing = User.query.filter(
        (User.email == admin_email) | (User.username == admin_user)
    ).first()
    if existing:
        return

    u = User(
        username=admin_user,
        email=admin_email,
        full_name="Administrator",
        is_active=True,
        is_admin=True,
    )
    u.set_password(admin_pass)
    db.session.add(u)
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_admin()

# -------------------------------------------------
# Health checks
# -------------------------------------------------
@app.get("/health")
def health_root():
    return {"status": "running"}, 200

@app.get("/api/health")
def health_api():
    return {"status": "ok"}, 200

# -------------------------------------------------
# Auth API
# -------------------------------------------------
@app.post("/api/auth/login")
def login():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"success": False, "error": "invalid_json"}), 400

    # الدعم للاسمين: واجهتك ترسل username/password — وأيضًا ندعم identifier
    identifier = (data.get("identifier") or data.get("username") or data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not identifier or not password:
        return jsonify({"success": False, "error": "missing_fields"}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.check_password(password) or not user.is_active:
        return jsonify({"success": False, "error": "invalid_credentials"}), 401

    session["user_id"] = user.id
    return jsonify({"success": True, "user": user.to_safe_dict()}), 200

@app.get("/api/auth/check-session")
def check_session():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"ok": False}), 401
    u = User.query.get(uid)
    if not u:
        session.clear()
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "user": u.to_safe_dict()})

@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

# -------------------------------------------------
# تقديم واجهة Vite (SPA)
# -------------------------------------------------
@app.get("/")
def spa_index():
    # index.html من مجلد build
    return send_from_directory(STATIC_DIR, "index.html")

# ملفات الأصول التي يبنيها Vite داخل /assets
@app.get("/assets/<path:asset_path>")
def spa_assets(asset_path):
    return send_from_directory(os.path.join(STATIC_DIR, "assets"), asset_path)

# أي مسار ليس api/* يرجع index.html لدعم راوتينغ الواجهة
@app.get("/<path:path>")
def spa_fallback(path):
    if path.startswith("api/"):
        return jsonify({"error": "not_found"}), 404
    # ملفات ثابتة أخرى (مثل /favicon.svg لو موجودة في static مباشرة)
    file_path = os.path.join(STATIC_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")

# -------------------------------------------------
# نقطة تشغيل غنوكورن
# -------------------------------------------------
# يقرأها gunicorn عبر: src.main:app
# لا حاجة لشيء إضافي هنا.
