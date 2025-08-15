# src/main.py
from __future__ import annotations

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------------------------------------------------------------
# تهيئة عامة
# -----------------------------------------------------------------------------
db = SQLAlchemy()

# مسار مجلد instance داخل الحاوية (مطلوب لـ SQLite)
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # /app/src -> /app
INSTANCE_DIR = PROJECT_ROOT / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# الموديل: المستخدم
# -----------------------------------------------------------------------------
class User(db.Model):  # type: ignore[misc]
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_safe_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
        }

# -----------------------------------------------------------------------------
# أدوات مساعدة
# -----------------------------------------------------------------------------
def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key, default)
    return v.strip() if isinstance(v, str) else v

def _database_uri() -> str:
    # أولوية: SQLALCHEMY_DATABASE_URI ثم DATABASE_URL ثم SQLite افتراضي
    uri = _get_env("SQLALCHEMY_DATABASE_URI") or _get_env("DATABASE_URL")
    if not uri:
        # SQLite داخل /app/instance/app.db
        uri = "sqlite:////app/instance/app.db"
    # إصلاح شائع لـ sqlite:///relative/path
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        # اجعل المسار مطلق داخل /app
        relative = uri.replace("sqlite:///", "", 1)
        uri = f"sqlite:////app/{relative}"
    return uri

def _admin_from_env() -> dict:
    return {
        "username": _get_env("ADMIN_USERNAME", "admin"),
        "email": _get_env("ADMIN_EMAIL", "admin@example.com"),
        "password": _get_env("ADMIN_PASSWORD", "Admin@1234"),
        "full_name": _get_env("ADMIN_FULL_NAME", "Administrator"),
    }

def _validate_password(pw: str) -> bool:
    # بسيط: 8+ حروف وفيه أحرف كبيرة/صغيرة/أرقام/رمز (مرن)
    if len(pw) < 8:
        return False
    categories = sum([
        bool(re.search(r"[A-Z]", pw)),
        bool(re.search(r"[a-z]", pw)),
        bool(re.search(r"\d", pw)),
        bool(re.search(r"[^A-Za-z0-9]", pw)),
    ])
    return categories >= 3

# -----------------------------------------------------------------------------
# إنشاء التطبيق
# -----------------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(PROJECT_ROOT / "static"), static_url_path="/")

    # سر التطبيق
    app.config["SECRET_KEY"] = _get_env("SECRET_KEY") or "rfah-secret-key"

    # قاعدة البيانات
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # CORS (السماح للواجهة بالوصول إلى API)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # تهيئة DB
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _seed_admin_if_missing()

    # ------------------ Health ------------------
    @app.get("/health")
    def health() -> tuple[dict, int]:
        return {"status": "running"}, 200

    # ------------------ Auth: Login ------------------
    @app.post("/api/auth/login")
    def api_login():
        """
        يقبل:
        {
          "identifier": "admin@example.com" أو "admin",
          "password": "Admin@1234"
        }
        """
        try:
            data = request.get_json(silent=True) or {}
            identifier = (data.get("identifier") or "").strip()
            password = data.get("password") or ""

            if not identifier or not password:
                return jsonify({"ok": False, "error": "missing_fields"}), 400

            # ابحث بالـ email أو username
            user = None
            if "@" in identifier:
                user = User.query.filter_by(email=identifier).first()
            if user is None:
                user = User.query.filter_by(username=identifier).first()

            if not user or not user.is_active:
                return jsonify({"ok": False, "error": "invalid_credentials"}), 401

            if not user.check_password(password):
                return jsonify({"ok": False, "error": "invalid_credentials"}), 401

            # نجاح
            return jsonify({"ok": True, "user": user.to_safe_dict()}), 200

        except Exception as e:
            return jsonify({"ok": False, "error": "server_error", "detail": str(e)}), 500

    # ------------------ Admin: Reset/Seed ------------------
    @app.post("/api/auth/reset-admin")
    def api_reset_admin():
        """
        يحميه ADMIN_SETUP_KEY
        - أرسل المفتاح هيدر: X-Admin-Setup-Key
          أو كـ query: ?key=VALUE
        - يعيد إنشاء/تحديث حساب المدير من متغيرات البيئة
        """
        setup_key_env = _get_env("ADMIN_SETUP_KEY", "")
        provided = request.headers.get("X-Admin-Setup-Key") or request.args.get("key") or ""
        if not setup_key_env:
            return jsonify({"ok": False, "error": "setup_key_not_configured"}), 400
        if provided != setup_key_env:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

        # force=True لتحديث البيانات إن كانت موجودة
        changed = _seed_admin(force=True)
        return jsonify({"ok": True, "changed": changed}), 200

    # ------------------ خدمة ملفات الواجهة (اختياري) ------------------
    @app.get("/")
    def index():
        # إذا وُجد index.html داخل static سيتم تقديمه
        index_path = Path(app.static_folder or "") / "index.html"
        if index_path.is_file():
            return send_from_directory(app.static_folder, "index.html")
        return jsonify({"status": "running"}), 200

    return app

# -----------------------------------------------------------------------------
# تهيئة/زرع حساب المدير
# -----------------------------------------------------------------------------
def _seed_admin_if_missing() -> None:
    """إنشاء حساب المدير فقط إن لم يوجد (تجنب تكرار البريد)."""
    env = _admin_from_env()
    user = User.query.filter(
        (User.email == env["email"]) | (User.username == env["username"])
    ).first()
    if user is None:
        user = User(
            username=env["username"],
            email=env["email"],
            full_name=env["full_name"],
            is_active=True,
            is_admin=True,
        )
        pw = env["password"] or "Admin@1234"
        if not _validate_password(pw):
            pw = "Admin@1234"
        user.set_password(pw)
        db.session.add(user)
        db.session.commit()

def _seed_admin(force: bool = False) -> dict:
    """
    إنشاء/تحديث حساب المدير حسب متغيرات البيئة.
    يعيد dict فيها تفاصيل ماذا حدث.
    """
    env = _admin_from_env()
    result = {"created": False, "updated": False}

    user = User.query.filter(
        (User.email == env["email"]) | (User.username == env["username"])
    ).first()

    if user is None:
        # إنشاء
        user = User(
            username=env["username"],
            email=env["email"],
            full_name=env["full_name"],
            is_active=True,
            is_admin=True,
        )
        pw = env["password"] or "Admin@1234"
        if not _validate_password(pw):
            pw = "Admin@1234"
        user.set_password(pw)
        db.session.add(user)
        db.session.commit()
        result["created"] = True
    elif force:
        # تحديث
        changed = False

        # لو تغيرت الـ username/email في البيئة نحدّثهما
        if user.username != env["username"]:
            # تأكد من عدم وجود اسم مستخدم مطابق
            other_u = User.query.filter(User.username == env["username"], User.id != user.id).first()
            if other_u is None:
                user.username = env["username"]
                changed = True

        if user.email != env["email"]:
            other_e = User.query.filter(User.email == env["email"], User.id != user.id).first()
            if other_e is None:
                user.email = env["email"]
                changed = True

        if env["full_name"] and user.full_name != env["full_name"]:
            user.full_name = env["full_name"]
            changed = True

        if env["password"] and _validate_password(env["password"]):
            user.set_password(env["password"])
            changed = True

        if changed:
            db.session.commit()
            result["updated"] = True

    return result

# -----------------------------------------------------------------------------
# نقطة دخول جاهزة لِـ gunicorn: "src.main:app"
# -----------------------------------------------------------------------------
app = create_app()

# للتشغيل محليًا: python -m src.main
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
