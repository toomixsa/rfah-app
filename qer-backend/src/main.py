# src/main.py
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from flask_cors import CORS  # type: ignore
except Exception:  # حيلة في حال لم تُثبَّت المكتبة
    CORS = lambda app, **_: app  # noqa: E731

# -----------------------------
# إعداد المسارات العامة
# -----------------------------
APP_DIR = Path(__file__).resolve().parent  # عادةً src/
ROOT_DIR = APP_DIR.parent                   # جذر الباك
INSTANCE_DIR = Path("/app/instance")        # يتوافق مع Dockerfile
STATIC_BUNDLE = Path("/bundle-static")      # ننسخ إليه واجهة الفرونت

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# قاعدة البيانات
# -----------------------------
db = SQLAlchemy()


def get_db_uri() -> str:
    # نحترم أي من المتغيرين إن وُجد
    uri = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or os.getenv("DATABASE_URI")
        or os.getenv("DATABASE_URL".upper())
        or os.getenv("DATABASE_URI".upper())
    )
    if uri:
        return uri
    # افتراضي: SQLite داخل مجلد instance
    return "sqlite:////app/instance/app.db"


# -----------------------------
# نموذج المستخدم
# سنحاول استيراده من مشروعك، وإن فشل نعرّفه هنا
# -----------------------------
User = None  # type: ignore


def _define_inline_models():
    """تعريف نموذج User بديل في حال لم يوجد داخل مشروعك."""
    class _User(db.Model):  # type: ignore
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
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

    return _User


try:
    # جرّب مسارات مألوفة داخل مشاريع Flask
    # (عدّل المسارات حسب هيكلتك إن لزم)
    from src.models.user import User as _User  # type: ignore
    User = _User
except Exception:
    try:
        from models.user import User as _User  # type: ignore
        User = _User
    except Exception:
        # سنستخدم النموذج الداخلي
        User = _define_inline_models()


# -----------------------------
# تهيئة التطبيق
# -----------------------------
def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(STATIC_BUNDLE),   # نخلي Flask يعرف مجلد الواجهة
        static_url_path="",                  # بحيث تكون الملفات على /
    )

    # مفتاح سرّي
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "change-me-please-very-long"
    )

    # قاعدة البيانات
    app.config["SQLALCHEMY_DATABASE_URI"] = get_db_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

    # أنشئ الجداول (SQLite) إن لم تكن موجودة
    with app.app_context():
        db.create_all()
        _seed_admin()

    # -------------------------
    # Health checks
    # -------------------------
    @app.get("/health")
    def health_root():
        return jsonify(status="running"), 200

    @app.get("/api/health")
    def health_api():
        return jsonify(status="running"), 200

    # -------------------------
    # API: تسجيل الدخول
    # -------------------------
    @app.post("/api/login")
    def api_login():
        # يدعم JSON و x-www-form-urlencoded
        payload = request.get_json(silent=True) or request.form or {}
        identity = (payload.get("identity") or payload.get("username") or payload.get("email") or "").strip()
        password = (payload.get("password") or "").strip()

        if not identity or not password:
            return jsonify(error="missing_fields"), 400

        # ابحث باليوزرنيم أو الإيميل
        user = (
            User.query.filter((User.username == identity) | (User.email == identity))
            .first()
        )

        if not user or not getattr(user, "is_active", True):
            return jsonify(error="invalid_credentials"), 401

        if not user.check_password(password):
            return jsonify(error="invalid_credentials"), 401

        # نجعل الاستجابة بسيطة ومباشرة
        return jsonify(status="ok", user={"username": user.username, "email": user.email, "is_admin": bool(getattr(user, "is_admin", False))}), 200

    # -------------------------
    # خدمة واجهة الفرونت (SPA)
    # -------------------------
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path: str):
        """
        - يقدّم أي ملف ثابت إن وُجد في /bundle-static
        - وإلا يُرجع index.html كـ fallback (تطبيق SPA)
        """
        # ملف فعلي؟
        candidate = STATIC_BUNDLE / path
        if path and candidate.exists() and candidate.is_file():
            return send_from_directory(str(STATIC_BUNDLE), path)

        # fallback إلى index.html إن وُجد
        index_file = STATIC_BUNDLE / "index.html"
        if index_file.exists():
            return send_from_directory(str(STATIC_BUNDLE), "index.html")

        # إن لم توجد واجهة مبنية
        return jsonify(status="running"), 200

    return app


# -----------------------------
# تهيئة/زرع حساب الأدمن
# -----------------------------
def _seed_admin() -> None:
    """
    يزرع حساب أدمن فقط إن لم يوجد (حسب الإيميل أو اليوزرنيم).
    يستخدم:
      ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME
    """
    email = os.getenv("ADMIN_EMAIL", "").strip() or "admin@example.com"
    username = os.getenv("ADMIN_USERNAME", "").strip() or "admin"
    password = os.getenv("ADMIN_PASSWORD", "").strip() or "Admin@1234"

    # موجود مسبقاً؟
    exists = User.query.filter(
        (User.email == email) | (User.username == username)
    ).first()
    if exists:
        return

    user = User(
        username=username,
        email=email,
        full_name="Administrator",
        is_active=True,
        is_admin=True,
    )
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # نتجاهل لو تعارضت UNIQUE، حفاظاً على الإقلاع
        # بإمكانك تسجيلها في logs إذا رغبت


# متغيّر التطبيق الذي يقرأه Gunicorn:  src.main:app
app = create_app()

# تشغيل محلياً لو أردت:
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
