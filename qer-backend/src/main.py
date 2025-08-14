# qer-backend/src/main.py
import os
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    send_from_directory,
    jsonify,
    request,
    session,
    redirect,
)
from werkzeug.middleware.proxy_fix import ProxyFix

# نماذج وقاعدة البيانات
from models import db, User

# البلوب برنتس (موجودة في مشروعك)
from routes.auth import auth_bp
from routes.urls import urls_bp

# إعداد المجلدات
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_STATIC = BASE_DIR / "static"   # سننسخ إليها build الواجهة
DEFAULT_INSTANCE = BASE_DIR / "instance"

def get_database_uri() -> str:
    # أولوية للمتغير ENV إن وُجد، وإلا SQLite محلي داخل instance
    env_uri = os.getenv("DATABASE_URL") or os.getenv("DB_URI") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if env_uri:
        return env_uri
    instance_dir = os.getenv("INSTANCE_DIR", str(DEFAULT_INSTANCE))
    Path(instance_dir).mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{Path(instance_dir) / 'app.db'}"

def create_app() -> Flask:
    static_dir = os.getenv("STATIC_DIR", str(DEFAULT_STATIC))
    Path(static_dir).mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, static_folder=static_dir, static_url_path="/")

    # خلف بروكسي (مثل Koyeb)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # مفاتيح وتكوينات
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.getenv("FLASK_ENV") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    # قاعدة البيانات
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # تسجيل البلوب برنتس تحت /api
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(urls_bp, url_prefix="/api/urls")

    # فحص صحي
    @app.get("/api/health")
    def health():
        return jsonify({"status": "running"})

    # مسار جذر: يخدم index.html من الواجهة المبنية
    @app.get("/")
    def root():
        index_path = Path(app.static_folder) / "index.html"
        if index_path.exists():
            return send_from_directory(app.static_folder, "index.html")
        return redirect("/api/health")

    # إنشاء الجداول وتلقيم مستخدم إداري أول مرة
    with app.app_context():
        db.create_all()
        seed_admin()

    return app

def seed_admin():
    """إنشاء مستخدم إداري افتراضي إذا لم يوجد."""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    existing = User.query.filter(
        (User.username == admin_username) | (User.email == admin_email)
    ).first()
    if existing:
        return

    user = User(
        username=admin_username,
        email=admin_email,
        full_name="Administrator",
        is_active=True,
    )
    user.set_password(admin_password)
    db.session.add(user)
    db.session.commit()

# كائن التطبيق الذي يستعمله gunicorn
app = create_app()

if __name__ == "__main__":
    # تشغيل محلياً
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
