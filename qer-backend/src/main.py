import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, redirect
from werkzeug.middleware.proxy_fix import ProxyFix

# النماذج وقاعدة البيانات
from .models import db, User

# حاول تحميل البلوبرِنتات بشكل آمن
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
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.getenv("FLASK_ENV") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # سجّل البلوبرِنتات فقط إذا وُجدت
    if HAS_AUTH:
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
    if HAS_URLS:
        app.register_blueprint(urls_bp, url_prefix="/api/urls")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "running"})

    @app.get("/")
    def root():
        index_path = Path(app.static_folder) / "index.html"
        if index_path.exists():
            return send_from_directory(app.static_folder, "index.html")
        return redirect("/api/health")

    with app.app_context():
        db.create_all()
        seed_admin()

    return app

def seed_admin():
    from sqlalchemy import or_
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    existing = User.query.filter(or_(User.username == admin_username, User.email == admin_email)).first()
    if existing:
        return

    user = User(
        username=admin_username,
        email=admin_email,
        full_name="Administrator",
        is_active=True,
        is_admin=True,
    )
    user.set_password(admin_password)
    db.session.add(user)
    db.session.commit()

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
