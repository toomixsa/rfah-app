# qer-backend/src/main.py
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory, abort
from src.extensions import db

# CORS اختياري (لو الحزمة مثبتة)
try:
    from flask_cors import CORS  # type: ignore
except Exception:
    CORS = lambda *a, **k: None  # no-op لو غير مثبتة

# مسارات ثابتة
INSTANCE_DIR = Path("/app/instance")
STATIC_DIR = os.getenv("FRONTEND_DIR", "/app/src/static")  # يطابق Dockerfile

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def _database_uri() -> str:
    uri = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or "sqlite:////app/instance/app.db"
    )
    # تصحيح sqlite النسبي إن وُجد
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        rel = uri.replace("sqlite:///", "", 1)
        uri = f"sqlite:////app/{rel}"
    return uri


def create_app() -> Flask:
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-please")
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # اربط SQLAlchemy بهذا التطبيق
    db.init_app(app)

    # فعّل CORS لمسارات API
    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

    # سجّل الموديلات وأنشئ الجداول وازرع الأدمن (مرة واحدة)
    with app.app_context():
        from src.models.user import User  # noqa: F401
        db.create_all()
        _seed_admin()

    # ---------- Health ----------
    @app.get("/health")
    def health_root():
        return jsonify(status="running"), 200

    @app.get("/api/health")
    def health_api():
        return jsonify(status="running"), 200

    # ---------- Auth: Login ----------
    @app.post("/api/auth/login")
    def api_login():
        from src.models.user import User

        data = request.get_json(silent=True) or request.form or {}
        identifier = (
            (data.get("identifier") or data.get("email") or data.get("username") or "").strip()
        )
        password = (data.get("password") or data.get("pass") or "").strip()

        if not identifier or not password:
            return jsonify(error="missing_fields"), 400

        user = (
            User.query.filter((User.username == identifier) | (User.email == identifier))
            .first()
        )
        if not user or not user.is_active or not user.check_password(password):
            return jsonify(error="invalid_credentials"), 401

        return jsonify(
            ok=True,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": bool(user.is_admin),
            },
        ), 200

    # ---------- تقديم واجهة الفرونت (SPA) ----------
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path: str):
        # لا نلتقط مسارات الـ API
        if path.startswith("api/"):
            abort(404)

        file_path = Path(STATIC_DIR) / path
        if path and file_path.exists() and file_path.is_file():
            return send_from_directory(STATIC_DIR, path)

        index_file = Path(STATIC_DIR) / "index.html"
        if index_file.exists():
            return send_from_directory(STATIC_DIR, "index.html")

        # لو ما فيه build، رجّع JSON مؤقتًا
        return jsonify(status="running"), 200

    return app


def _seed_admin() -> None:
    """زرع أدمن مرة واحدة فقط إذا غير موجود."""
    from src.models.user import User

    email = (os.getenv("ADMIN_EMAIL") or "admin@example.com").strip()
    username = (os.getenv("ADMIN_USERNAME") or "admin").strip()
    password = (os.getenv("ADMIN_PASSWORD") or "Admin@1234").strip()

    exists = User.query.filter(
        (User.email == email) | (User.username == username)
    ).first()
    if exists:
        return

    u = User(
        username=username,
        email=email,
        full_name="Administrator",
        is_active=True,
        is_admin=True,
        created_at=datetime.utcnow(),
    )
    u.set_password(password)
    db.session.add(u)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


# نقطة دخول لـ gunicorn: src.main:app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
