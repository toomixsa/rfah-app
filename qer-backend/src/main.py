# src/main.py
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
from src.extensions import db  # <-- نفس الإنستانس

# مسارات مفيدة
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # /app/src -> /app
INSTANCE_DIR = Path("/app/instance")
STATIC_BUNDLE = Path("/bundle-static")  # Dockerfile ينسخ بناء الفرونت هنا

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

def _database_uri() -> str:
    uri = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or "sqlite:////app/instance/app.db"
    )
    # إصلاح sqlite النسبي
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        rel = uri.replace("sqlite:///", "", 1)
        uri = f"sqlite:////app/{rel}"
    return uri

def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_BUNDLE), static_url_path="")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-please")
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # اربط الإنستانس بالتطبيق (هذه نقطة الخطأ عندك)
    db.init_app(app)

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

    # يجب استيراد الموديلات بعد init_app حتى تُسجّل على نفس الـ db
    with app.app_context():
        from src.models.user import User  # noqa: F401
        db.create_all()
        _seed_admin()  # ينشئ الأدمن إذا غير موجود

    # -------- Health --------
    @app.get("/health")
    def health_root():
        return jsonify(status="running"), 200

    @app.get("/api/health")
    def health_api():
        return jsonify(status="running"), 200

    # -------- Auth: Login --------
    @app.post("/api/auth/login")
    def api_login():
        from src.models.user import User
        data = request.get_json(silent=True) or request.form or {}
        identifier = (data.get("identifier") or data.get("email") or data.get("username") or "").strip()
        password   = (data.get("password")   or data.get("pass")   or "").strip()

        if not identifier or not password:
            return jsonify(error="missing_fields"), 400

        user = (
            User.query.filter((User.username == identifier) | (User.email == identifier))
            .first()
        )
        if not user or not user.is_active or not user.check_password(password):
            return jsonify(error="invalid_credentials"), 401

        return jsonify(ok=True, user={"id": user.id, "username": user.username, "email": user.email, "is_admin": bool(user.is_admin)}), 200

    # -------- تقديم واجهة الفرونت (SPA) --------
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path: str):
        # لا نلتقط مسارات الـ API
        if path.startswith("api/"):
            abort(404)

        candidate = STATIC_BUNDLE / path
        if path and candidate.exists() and candidate.is_file():
            return send_from_directory(str(STATIC_BUNDLE), path)

        index_file = STATIC_BUNDLE / "index.html"
        if index_file.exists():
            return send_from_directory(str(STATIC_BUNDLE), "index.html")

        return jsonify(status="running"), 200  # في حال ما فيه فرونت مبني

    return app

def _seed_admin() -> None:
    """زرع أدمن مرة واحدة فقط إذا غير موجود."""
    from src.models.user import User
    email = (os.getenv("ADMIN_EMAIL") or "admin@example.com").strip()
    username = (os.getenv("ADMIN_USERNAME") or "admin").strip()
    password = (os.getenv("ADMIN_PASSWORD") or "Admin@1234").strip()

    exists = User.query.filter((User.email == email) | (User.username == username)).first()
    if exists:
        return

    u = User(username=username, email=email, full_name="Administrator", is_active=True, is_admin=True)
    u.set_password(password)
    db.session.add(u)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

# نقطة دخول لـ gunicorn: "src.main:app"
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
