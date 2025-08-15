# qer-backend/src/main.py
import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, redirect
from werkzeug.middleware.proxy_fix import ProxyFix

from .models import db, User

# جرّب تحميل البلوبرنتات بشكل آمن (حتى لو ملف مفقود ما ينهار السيرفر)
HAS_AUTH = HAS_URLS = False
try:
    from .routes.auth import auth_bp
    HAS_AUTH = True
except Exception as e:
    print("[init] auth blueprint not loaded:", e)

try:
    from .routes.urls import urls_bp
    HAS_URLS = True
except Exception as e:
    print("[init] urls blueprint not loaded:", e)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_STATIC = BASE_DIR / "static"
DEFAULT_INSTANCE = BASE_DIR / "instance"


def get_database_uri() -> str:
    """يعيد URI قاعدة البيانات من المتغيرات، وإلا SQLite داخل instance/"""
    env_uri = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URI")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
    )
    if env_uri:
        return env_uri
    instance_dir = os.getenv("INSTANCE_DIR", str(DEFAULT_INSTANCE))
    Path(instance_dir).mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{Path(instance_dir) / 'app.db'}"


def create_app() -> Flask:
    # المكان الذي ننسخ إليه مخرجات Vite (dist) في Dockerfile
    static_dir = os.getenv("STATIC_DIR", str(DEFAULT_STATIC))
    Path(static_dir).mkdir(parents=True, exist_ok=True)

    # نخدم الأصول تحت /static
    app = Flask(__name__, static_folder=static_dir, static_url_path="/static")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # إعدادات عامة
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.getenv("FLASK_ENV") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    # قاعدة البيانات
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # تسجيل البلوبرنتات إذا كانت موجودة
    if HAS_AUTH:
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
    if HAS_URLS:
        app.register_blueprint(urls_bp, url_prefix="/api/urls")

    # فحص صحي
    @app.get("/api/health")
    def health():
        return jsonify({"status": "running"})

    @app.get("/api/status")
    def status():
        return jsonify({"status": "ok"})

    # الصفحة الرئيسية: قدّم index.html من static
    @app.get("/")
    def root():
        index_path = Path(app.static_folder) / "index.html"
        if index_path.exists():
            return send_from_directory(app.static_folder, "index.html")
        return redirect("/api/health")

    # SPA fallback: أي مسار ليس API وليس ملفاً فعلياً → أعد index.html
    @app.get("/<path:path>")
    def spa_fallback(path: str):
        # لا نتدخل في /api/* — اتركها للبلوبرنتات
        if path.startswith("api/"):
            return jsonify(error="not found"), 404

        file_path = Path(app.static_folder) / path
        if file_path.exists():
            return send_from_directory(app.static_folder, path)

        index_path = Path(app.static_folder) / "index.html"
        if index_path.exists():
            return send_from_directory(app.static_folder, "index.html")

        return jsonify(error="frontend_not_built"), 500

    # أنشئ الجداول وازرع مستخدم أدمن مرة واحدة
    with app.app_context():
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    """زرع مستخدم أدمن مع حماية من التعارض بين العمال."""
    from sqlalchemy import select, or_
    from sqlalchemy.exc import IntegrityError

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    # تحقّق مسبق
    stmt = select(User).filter(
        or_(User.username == admin_username, User.email == admin_email)
    )
    existing = db.session.execute(stmt).scalar_one_or_none()
    if existing:
        print("[seed] admin already exists, skipping.")
        return

    try:
        u = User(
            username=admin_username,
            email=admin_email,
            full_name="Administrator",
            is_active=True,
            is_admin=True,
        )
        u.set_password(admin_password)
        db.session.add(u)
        db.session.commit()
        print(f"[seed] created admin: {admin_username} / {admin_password}")
    except IntegrityError:
        db.session.rollback()
        print("[seed] admin was created by another worker; skipping.")


# مهم: تعيين app خارج أي شرط لكي يراه Gunicorn: src.main:app
app = create_app()

# للتشغيل المحلي فقط
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
