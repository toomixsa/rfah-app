import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.url import url_bp
from src.routes.auth import auth_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# تمكين CORS للسماح بالطلبات من الواجهة الأمامية مع دعم الجلسات
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(url_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # إنشاء مستخدمين افتراضيين للاختبار
    from src.models.user import User
    
    # التحقق من وجود المسؤول
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@qer.me',
            password='admin123',
            full_name='مدير النظام',
            is_admin=True
        )
        db.session.add(admin_user)
        
        # إنشاء موظف تجريبي
        employee_user = User(
            username='employee1',
            email='employee1@qer.me',
            password='123456',
            full_name='أحمد محمد',
            is_admin=False
        )
        db.session.add(employee_user)
        
        # إنشاء موظف آخر
        employee2_user = User(
            username='employee2',
            email='employee2@qer.me',
            password='123456',
            full_name='فاطمة علي',
            is_admin=False
        )
        db.session.add(employee2_user)
        
        db.session.commit()
        print("تم إنشاء المستخدمين الافتراضيين:")
        print("المسؤول: admin@qer.me / admin123")
        print("الموظف 1: employee1@qer.me / 123456")
        print("الموظف 2: employee2@qer.me / 123456")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

