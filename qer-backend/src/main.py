# ---------------------------------------------------------
# Bootstrap admin (idempotent) — يُنشئ/يحدّث أدمن عند الإقلاع
# ضع هذا المقطع بعد إنشاء app و db واستيراد نموذج User
# ---------------------------------------------------------
import os
from werkzeug.security import generate_password_hash

# حاول الاستيراد من مسارَيّن شائعين، عدّل إذا لزم
try:
    from src.models import User
except Exception:
    from models import User  # بديل

def _set_password(user, raw_password: str):
    """يضبط كلمة المرور حسب أسلوب النموذج لديك."""
    if hasattr(user, "set_password") and callable(getattr(user, "set_password")):
        user.set_password(raw_password)
    elif hasattr(user, "password_hash"):
        user.password_hash = generate_password_hash(raw_password)
    else:
        # بعض النماذج تستخدم حقل "password" كمخزن للهاش
        user.password = generate_password_hash(raw_password)

def bootstrap_admin_from_env():
    """ينشئ/يحدّث حساب الأدمن استنادًا إلى متغيرات البيئة (أو القيم المقترَحة)."""
    email = os.getenv("ADMIN_EMAIL", "admin@rafah.local").strip()
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe_987!").strip()
    name = os.getenv("ADMIN_NAME", "Rafah Admin").strip()
    role_value = os.getenv("ADMIN_ROLE", "admin").strip()

    # لا تعمل شيئًا إذا قيم البيئة فارغة عمدًا
    if not email or not password:
        print("[bootstrap] ADMIN_EMAIL/ADMIN_PASSWORD not provided -> skip")
        return

    from flask import current_app
    with current_app.app_context():
        # تأكد من وجود الجداول
        try:
            db.create_all()
        except Exception as e:
            print(f"[bootstrap] db.create_all() failed: {e}")

        # ابحث بالمفاتيح المتاحة في النموذج (email / username)
        u = None
        if hasattr(User, "email"):
            u = User.query.filter_by(email=email).first()
        if not u and hasattr(User, "username"):
            u = User.query.filter_by(username=email).first()

        if u:
            # تحديث كلمة المرور والاسم/الدور إن لزم
            _set_password(u, password)
            if hasattr(u, "name") and name:
                u.name = name
            if hasattr(u, "role") and role_value:
                u.role = role_value
            db.session.commit()
            print(f"[bootstrap] admin updated: {email}")
        else:
            # إنشاء مستخدم جديد
            attrs = {}
            if hasattr(User, "email"):
                attrs["email"] = email
            if hasattr(User, "username"):
                # إن كان نموذجك يعتمد username فقط، استخدم البريد كاسم مستخدم
                attrs["username"] = email
            if hasattr(User, "name"):
                attrs["name"] = name
            if hasattr(User, "role"):
                attrs["role"] = role_value

            u = User(**attrs)
            _set_password(u, password)
            db.session.add(u)
            db.session.commit()
            print(f"[bootstrap] admin created: {email}")

# استدعاء البوتستراب عند الإقلاع
try:
    bootstrap_admin_from_env()
except Exception as e:
    print(f"[bootstrap] failed: {e}")
# ---------------------------------------------------------
