from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError

def seed_admin():
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    # افحص إن كان موجودًا مسبقًا
    stmt = select(User).filter(or_(User.username == admin_username, User.email == admin_email))
    existing = db.session.execute(stmt).scalar_one_or_none()
    if existing:
        print("[seed] admin already exists, skipping.")
        return

    # جرّب الإدخال وتجاهل التعارض لو حصل (بسبب سباق بين وركرز)
    try:
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
        print(f"[seed] created admin: {admin_username} / {admin_password}")
    except IntegrityError:
        db.session.rollback()
        print("[seed] admin was created by another worker; skipping.")
