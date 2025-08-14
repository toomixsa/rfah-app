# qer-backend/src/main.py
import os
import importlib
import pkgutil
from flask import Flask, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, select, update, insert
from werkzeug.security import generate_password_hash

# -----------------------------
# إعداد قاعدة البيانات
# -----------------------------
db = SQLAlchemy()


def _db_uri_from_env() -> str:
    """يقرأ مسار القاعدة من المتغيرات، وإلا يستخدم SQLite داخل /app/instance/app.db"""
    uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    if not uri:
        uri = "sqlite:////app/instance/app.db"  # أربع شرطات لمسار مطلق
    return uri


def _ensure_sqlite_dir(uri: str) -> None:
    """إن كانت SQLite بملف، أنشئ مجلد الملف قبل الاتصال."""
    if not uri.startswith("sqlite:"):
        return
    # sqlite:////absolute/path.db  -> /absolute/path.db
    if uri.startswith("sqlite:////"):
        db_path = uri.replace("sqlite:////", "/", 1)
    # sqlite:///relative/path.db   -> اجعله مطلقًا
    elif uri.startswith("sqlite:///"):
        rel = uri.replace("sqlite:///", "", 1)
        db_path = os.path.abspath(rel)
    else:
        # مثل sqlite:///:memory:
        return
    os.makedirs(os.path.dirname(db_path), exist_ok=True)


# -----------------------------
# إنشاء تطبيق Flask
# -----------------------------
def create_app() -> Flask:
    # نعرض الواجهة من /app/src/static (حسب Dockerfile)
    app = Flask(__name__, static_folder="src/static", static_url_path="/")

    # مفاتيح عامة
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

    # قاعدة البيانات
    db_uri = _db_uri_from_env()
    _ensure_sqlite_dir(db_uri)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # حاول استيراد الموديلات تلقائيًا (لو عندك حزمة src/models أو src/db/models)
    _auto_import_models(["src.models", "src.db.models"])

    # أنشئ الجداول (إن كانت الموديلات معرَّفة)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"[init] db.create_all() skipped/failed: {e}")

    # نفّذ Bootstrap Admin بالانعكاس (لا يعتمد على كلاس User)
    try:
        bootstrap_admin_reflect(app)
    except Exception as e:
        print(f"[bootstrap] failed: {e}")

    # فحص صحي سريع
    @app.get("/healthz")
    def healthz():
        return "ok", 200

    # خدمة SPA: أي مسار غير موجود يُعاد إلى index.html
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path: str):
        index_path = os.path.join(app.static_folder, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, "index.html")
        return jsonify({"status": "running"}), 200

    return app


def _auto_import_models(packages: list[str]) -> None:
    """
    يحاول استيراد جميع الموديلات داخل الحِزَم المحددة حتى تُسجَّل في SQLAlchemy.
    لا يفشل حتى لو لم توجد الحزم.
    """
    for pkg_name in packages:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue
        # استورد الموديول نفسه (يدعم حالة ملف واحد src/models.py)
        # ثم استورد كل الوحدات الفرعية داخل الحزمة إن وجدت
        try:
            for _, modname, _ in pkgutil.iter_modules(pkg.__path__):  # type: ignore[attr-defined]
                full = f"{pkg_name}.{modname}"
                try:
                    importlib.import_module(full)
                except Exception as e:
                    print(f"[models] skip {full}: {e}")
        except Exception:
            # ليست حزمة (قد يكون ملفًا واحدًا)، الاستيراد أعلاه كافٍ
            pass


# -----------------------------
# Bootstrap Admin (Reflection)
# -----------------------------
def bootstrap_admin_reflect(app: Flask) -> None:
    """
    ينشئ/يحدّث حساب أدمن بدون استيراد كلاس User:
    - يبحث عن جدول فيه (email أو username) + (password_hash أو password)
    - يملأ/يحدّث كلمة المرور والاسم/الدور إن توفرت أعمدة لها
    """
    email = os.getenv("ADMIN_EMAIL", "admin@rafah.local").strip()
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe_987!").strip()
    name = os.getenv("ADMIN_NAME", "Rafah Admin").strip()
    role_value = os.getenv("ADMIN_ROLE", "admin").strip()

    if not email or not password:
        print("[bootstrap] ADMIN_EMAIL/ADMIN_PASSWORD not provided -> skip")
        return

    with app.app_context():
        engine = db.engine
        md = MetaData()
        md.reflect(bind=engine)

        # اختر جدول المستخدم المناسب
        candidates = []
        for t in md.tables.values():
            cols = set(c.name.lower() for c in t.columns)
            if (('email' in cols) or ('username' in cols)) and (('password_hash' in cols) or ('password' in cols)):
                candidates.append(t)

        if not candidates:
            print("[bootstrap] No suitable users table found; skip")
            return

        users = candidates[0]
        cols = {c.name.lower(): c for c in users.columns}

        key_name = 'email' if 'email' in cols else 'username'
        pwd_field = 'password_hash' if 'password_hash' in cols else 'password'
        name_field = 'name' if 'name' in cols else None
        # ندعم role نصي أو is_admin منطقي
        role_field = 'role' if 'role' in cols else ('is_admin' if 'is_admin' in cols else None)

        values = {key_name: email, pwd_field: generate_password_hash(password)}
        if name_field:
            values[name_field] = name
        if role_field:
            values[role_field] = True if role_field == 'is_admin' else role_value

        with engine.begin() as conn:
            row = conn.execute(select(users).where(users.c[key_name] == email)).first()
            if row:
                conn.execute(update(users).where(users.c[key_name] == email).values(values))
                print(f"[bootstrap] admin updated: {email}")
            else:
                conn.execute(insert(users).values(values))
                print(f"[bootstrap] admin created: {email}")


# كائن التطبيق الذي يستخدمه gunicorn: "src.main:app"
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
