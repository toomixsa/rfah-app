# qer-backend/src/main.py
import os
from flask import Flask, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _db_uri_from_env() -> str:
    """
    يختار عنوان قاعدة البيانات من المتغيرات البيئية:
    - SQLALCHEMY_DATABASE_URI أو DATABASE_URL
    - وإلا يستخدم SQLite داخل /app/instance/app.db
    """
    uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    if not uri:
        uri = "sqlite:////app/instance/app.db"  # أربع شرطات لمسار مطلق
    return uri


def _ensure_sqlite_dir(uri: str) -> None:
    """
    إذا كانت القاعدة SQLite بملف (وليس in-memory)، أنشئ مجلد الملف قبل الاتصال.
    """
    if not uri.startswith("sqlite:"):
        return

    # sqlite:////absolute/path.db  -> /absolute/path.db
    if uri.startswith("sqlite:////"):
        db_path = uri.replace("sqlite:////", "/", 1)
    # sqlite:///relative/path.db   -> /current/dir/relative/path.db (نحوّلها لمسار مطلق)
    elif uri.startswith("sqlite:///"):
        rel = uri.replace("sqlite:///", "", 1)
        db_path = os.path.abspath(rel)
    else:
        # حالات مثل sqlite:///:memory: لا تحتاج مجلد
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)


def create_app() -> Flask:
    # static_folder = "static" لأن Dockerfile ينسخ بناء الواجهة إلى /app/src/static
    app = Flask(__name__, static_folder="static", static_url_path="/")

    # سر التطبيق (يُؤخذ من SECRET_KEY إن وُجد)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

    # إعداد قاعدة البيانات
    db_uri = _db_uri_from_env()
    _ensure_sqlite_dir(db_uri)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # تهيئة SQLAlchemy
    db.init_app(app)

    # استورد نماذجك (إن وُجدت) قبل create_all ليتم إنشاء الجداول
    # غيّر الاستيراد حسب مكان ملفات الموديلات عندك (مثلاً: from .models.user import User)
    try:
        from . import models  # noqa: F401
    except Exception:
        # لو ما عندك ملفات models بعد، عادي
        pass

    # إنشاء الجداول (لن ينشئ شيئًا إن لم توجد نماذج)
    with app.app_context():
        db.create_all()

    # مسار صحي للفحص
    @app.get("/healthz")
    def healthz():
        return "ok", 200

    # خدمة SPA: أي مسار غير موجود يعاد توجيهه إلى index.html داخل static
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path: str):
        index_path = os.path.join(app.static_folder, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, "index.html")
        # احتياطي إن لم توجد واجهة مبنية
        return jsonify({"status": "running"}), 200

    return app


# كائن التطبيق الذي يستخدمه gunicorn: "src.main:app"
app = create_app()

if __name__ == "__main__":
    # تشغيل محليًا (اختياري)
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
