# src/main.py
import os
from typing import Optional

from flask import (
    Flask,
    send_from_directory,
    redirect,
    url_for,
    jsonify,
    render_template_string,
    request,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# حيث نسخنا ملفات الواجهة (index.html وغيرها) من مرحلة البناء
STATIC_DIR = os.getenv("STATIC_DIR", "/app/src/static")

db = SQLAlchemy()


def create_app() -> Flask:
    """
    يهيّئ التطبيق:
      - SECRET_KEY و إعدادات الجلسة
      - قاعدة البيانات (SQLite افتراضياً داخل /app/instance/app.db)
      - إنشاء الجداول مع زرع مدير افتراضي
      - مسارات API للمصادقة (+ مسارات الفحص)
      - خدمة ملفات الواجهة من STATIC_DIR
    """
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/")

    # ---- الإعدادات العامة ----
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    # تجعل الكوكي آمنة في الإنتاج
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.getenv("FLASK_ENV", "production") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    # اختيار URI قاعدة البيانات من المتغيرات أو SQLite افتراضياً
    DB_URI = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
    )
    if not DB_URI:
        os.makedirs("/app/instance", exist_ok=True)
        DB_URI = "sqlite:////app/instance/app.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    print(f"Using DB: {DB_URI}")

    # ---- تعريف/تهيئة قاعدة البيانات ----
    db.init_app(app)

    # نحاول استيراد User إن كان لديك models
    try:
        from src.models import User  # type: ignore
    except Exception:
        # نموذج بديل بسيط
        class User(db.Model):  # type: ignore
            __tablename__ = "users"
            id = db.Column(db.Integer, primary_key=True)
            username = db.Column(db.String(80), unique=True, nullable=False)
            email = db.Column(db.String(120), unique=True, nullable=False)
            password_hash = db.Column(db.String(255), nullable=False)
            is_admin = db.Column(db.Boolean, default=False)

    with app.app_context():
        db.create_all()

        # زرع مدير افتراضي (يمكن تعطيله بـ SEED_ADMIN=0)
        if os.getenv("SEED_ADMIN", "1") != "0":
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
            admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

            exists = (
                db.session.query(User)
                .filter((User.username == admin_username) | (User.email == admin_email))
                .first()
            )
            if not exists:
                u = User(
                    username=admin_username,
                    email=admin_email,
                    password_hash=generate_password_hash(admin_password),
                    is_admin=True,
                )
                db.session.add(u)
                db.session.commit()
                print(
                    f"Seeded default admin user: {admin_username} / {admin_password}"
                )

    # ---------- أدوات مساعدة ----------
    def _find_user(identifier: str) -> Optional["User"]:
        """يبحث بالاسم أو البريد."""
        return (
            db.session.query(User)
            .filter((User.username == identifier) | (User.email == identifier))
            .first()
        )

    def _serialize_user(u: "User"):
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": bool(u.is_admin),
        }

    # ---------- مسارات فحص ----------
    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/api/status")
    def api_status():
        return jsonify(status="running")

    # ---------- مسارات المصادقة ----------
    # نقبل المسارين لزيادة التوافق مع الواجهة
    @app.post("/api/login")
    @app.post("/api/auth/login")
    def api_login():
        """
        يقبل JSON أو x-www-form-urlencoded.
        الحقول المدعومة:
          - identifier (أولوية) أو email أو username
          - password
        """
        data = request.get_json(silent=True) or request.form
        identifier = (
            data.get("identifier")
            or data.get("email")
            or data.get("username")
            or ""
        ).strip()
        password = (data.get("password") or "").strip()

        if not identifier or not password:
            return jsonify(error="missing_credentials"), 400

        u = _find_user(identifier)
        if not u or not check_password_hash(u.password_hash, password):
            return jsonify(error="invalid_credentials"), 401

        # خزّن المستخدم في الجلسة
        session["uid"] = u.id
        return jsonify(user=_serialize_user(u))

    @app.post("/api/logout")
    @app.post("/api/auth/logout")
    def api_logout():
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/me")
    @app.get("/api/auth/me")
    def api_me():
        uid = session.get("uid")
        if not uid:
            return jsonify(user=None), 200
        u = db.session.get(User, uid)
        return jsonify(user=_serialize_user(u)) if u else (jsonify(user=None), 200)

    # ---------- خدمة الواجهة ----------
    @app.get("/")
    def root():
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(STATIC_DIR, "index.html")

        files_list = (
            "\n".join(sorted(os.listdir(STATIC_DIR)))
            if os.path.isdir(STATIC_DIR)
            else "Static directory not found"
        )
        return render_template_string(
            """
            <h3>Static index not found</h3>
            <p>STATIC_DIR: {{ static_dir }}</p>
            <pre style="white-space:pre-wrap">{{ files }}</pre>
            """,
            static_dir=STATIC_DIR,
            files=files_list,
        )

    @app.get("/<path:path>")
    def static_files(path: str):
        full = os.path.join(STATIC_DIR, path)
        if os.path.exists(full):
            return send_from_directory(STATIC_DIR, path)
        # سماح لتطبيقات SPA
        return redirect(url_for("root"))

    return app


# كائن التطبيق الذي يقرأه Gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
