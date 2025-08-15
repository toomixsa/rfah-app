# qer-backend/src/extensions.py
from flask_sqlalchemy import SQLAlchemy

# إنستانس واحد مشترك في كل المشروع
db = SQLAlchemy()
