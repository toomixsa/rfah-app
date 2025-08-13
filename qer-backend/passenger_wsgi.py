import sys
import os

# أضف مسار مشروعك إلى مسارات بايثون
sys.path.insert(0, os.path.dirname(__file__))

# قم بتغيير الدليل إلى مجلد مشروعك
os.chdir(os.path.dirname(__file__))

# قم بتحميل تطبيق Flask الخاص بك
from src.main import app as application

# قم بتعيين متغير البيئة لـ Flask (اختياري، ولكن يفضل)
os.environ["FLASK_ENV"] = "production"


