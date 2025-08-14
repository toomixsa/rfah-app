# src/main.py
import os
from flask import (
    Flask,
    send_from_directory,
    redirect,
    url_for,
    jsonify,
    render_template_string,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# مجلد الواجهة التي ينسخها الـDocker من مرحلة البناء إلى هذا المسار
STATIC_DIR = os.getenv("STATIC_DIR", "/app/src/static")

db = SQLAlchemy()


def create_app() -> Flask:
    """
    يضبط تطبيق Flask:
      - تهيئة سرّ الجلسة
      - إعداد قاعدة البيانات (SQLite افتراضياً داخل /app/instance/app.db)
      - إنشاء الجداول
      - إنشاء مستخدم مدير افتراضي
      - خدمة ملفات الواجهة (index.html وبقية الملفات) من STATIC_DIR
    """
    # نجعل static_folder = STATIC_DIR حتى نخدم ملفات الواجهة مباشرة
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/")

    # ---- الإعدادات العامة ----
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    # اختيار سلسلة الاتصال بقاعدة البيانات من المتغيرات البيئية (إن وُجدت) وإلا SQLite داخل /app/instance
    DB_URI = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
    )
    if not DB_URI:
        # تأكد من وجود مجلد instance لصلاحيات الكتابة داخل الحاوية
        os.makedirs("/app/instance", exist_ok=True)
        DB_URI = "sqlite:////app/instance/app.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    print(f"Using DB: {DB_URI}")

    # ---- تهيئة قاعدة البيانات ----
    db.init_app(app)

    with app.app_context():
        # نحاول استيراد User من src.models إن وُجد
        try:
            from src.models import User  # type: ignore
        except Exception:
            # نموذج بديل بسيط إن لم يكن لديك ملف models
            class User(db.Model):  # type: ignore
                __tablename__ = "users"
                id = db.Column(db.Integer, primary_key=True)
                username = db.Column(db.String(80), unique=True, nullable=False)
                email = db.Column(db.String(120), unique=True, nullable=False)
                password_hash = db.Column(db.String(255), nullable=False)
                is_admin = db.Column(db.Boolean, default=False)

        # إنشاء الجداول
        db.create_all()

        # ---- تهيئة حساب مدير افتراضي (مرة واحدة) ----
        # يمكنك التحكم بالقيم من المتغيرات البيئية:
        # ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD, SEED_ADMIN=0 لتعطيل الإنشاء
        if os.getenv("SEED_ADMIN", "1") != "0":
            from sqlalchemy import select

            exists = db.session.execute(select(User).limit(1)).scalar_one_or_none()
            if not exists:
                admin_username = os.getenv("ADMIN_USERNAME", "admin")
                admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
                admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

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

    # ---- مسارات خفيفة للفحص ----
    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/api/status")
    def api_status():
        return jsonify(status="running")

    # ---- خدمة الواجهة ----
    @app.get("/")
    def root():
        """يقدّم index.html إن وُجد، وإلا يظهر قائمة الملفات للمساعدة على التشخيص."""
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
        """
        يقدّم أي ملف موجود داخل STATIC_DIR.
        وإن لم يوجد، نعيد توجيه المستخدم إلى الجذر (لـ SPA).
        """
        full = os.path.join(STATIC_DIR, path)
        if os.path.exists(full):
            return send_from_directory(STATIC_DIR, path)
        return redirect(url_for("root"))

    return app


# كائن التطبيق الذي يقرأه Gunicorn
app = create_app()

# للتشغيل المحلي فقط: python -m src.main
if __name__ == "__main__":
    # يعطّل الـreloader لأنه قد يكرر عملية الإنشاء/التهيئة
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
