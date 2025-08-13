"""
التطبيق الرئيسي المحسن لنظام رفاه
يتضمن جميع التحسينات والميزات الجديدة
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# استيراد النماذج والمكونات
from src.models.user import db, User
from src.models.url import ShortenedUrl as URL
from src.models.role import Role, Permission
from src.models.analytics import ClickLog
from src.security import SecurityManager, AuditLogger
from src.analytics import AnalyticsEngine

# استيراد نقاط النهاية
from src.routes.auth import auth_bp
from src.routes.url import url_bp

def create_app(config_name='development'):
    """إنشاء تطبيق Flask مع جميع التحسينات"""
    
    app = Flask(__name__)
    
    # إعدادات التطبيق
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///rfah_system.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # إعدادات الأمان
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-here')
    app.config['MAX_LOGIN_ATTEMPTS'] = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
    app.config['LOCKOUT_DURATION'] = int(os.getenv('LOCKOUT_DURATION', '900'))  # 15 دقيقة
    app.config['RATE_LIMIT_REQUESTS'] = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    app.config['RATE_LIMIT_WINDOW'] = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))  # ساعة
    app.config['PASSWORD_MIN_LENGTH'] = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
    app.config['REQUIRE_STRONG_PASSWORD'] = os.getenv('REQUIRE_STRONG_PASSWORD', 'True').lower() == 'true'
    
    # إعدادات النطاق المخصص
    app.config['DOMAIN'] = os.getenv('DOMAIN', 'rfah.me')
    app.config['BASE_URL'] = os.getenv('BASE_URL', 'https://rfah.me')
    
    # تهيئة قاعدة البيانات
    db.init_app(app)
    
    # تهيئة CORS
    CORS(app, origins=['*'], supports_credentials=True)
    
    # تهيئة أنظمة الأمان والتحليلات
    security_manager = SecurityManager(app)
    audit_logger = AuditLogger(app)
    analytics_engine = AnalyticsEngine(app)
    
    # تسجيل نقاط النهاية
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(url_bp, url_prefix='/api/urls')
    
    # نقطة نهاية الصحة
    @app.route('/health')
    def health_check():
        """فحص صحة النظام"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'domain': app.config['DOMAIN']
        })
    
    # نقطة نهاية المعلومات
    @app.route('/api/info')
    def system_info():
        """معلومات النظام"""
        return jsonify({
            'name': 'نظام رفاه لاختصار الروابط',
            'version': '2.0.0',
            'domain': app.config['DOMAIN'],
            'features': [
                'اختصار الروابط المتقدم',
                'نظام إدارة المستخدمين والأدوار',
                'تحليلات وإحصائيات شاملة',
                'أمان متقدم ومراجعة شاملة',
                'واجهة عربية متجاوبة',
                'تقارير أداء مفصلة'
            ],
            'api_version': 'v1',
            'documentation': f"{app.config['BASE_URL']}/docs"
        })
    
    # معالج الأخطاء العام
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'المورد غير موجود'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'خطأ داخلي في الخادم'}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'غير مصرح لك بالوصول'}), 403
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
    
    # إنشاء الجداول والبيانات الأولية
    with app.app_context():
        db.create_all()
        create_initial_data()
    
    return app

def create_initial_data():
    """إنشاء البيانات الأولية للنظام"""
    
    # إنشاء الأدوار الأساسية
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(
            name='admin',
            display_name='مدير النظام',
            description='مدير النظام مع جميع الصلاحيات',
            is_system=True
        )
        db.session.add(admin_role)
    
    user_role = Role.query.filter_by(name='user').first()
    if not user_role:
        user_role = Role(
            name='user',
            display_name='مستخدم عادي',
            description='مستخدم عادي مع صلاحيات أساسية',
            is_system=True
        )
        db.session.add(user_role)
    
    moderator_role = Role.query.filter_by(name='moderator').first()
    if not moderator_role:
        moderator_role = Role(
            name='moderator',
            display_name='مشرف',
            description='مشرف مع صلاحيات متوسطة',
            is_system=True
        )
        db.session.add(moderator_role)
    
    # إنشاء الصلاحيات الأساسية
    permissions_data = [
        # صلاحيات الروابط
        ('url.create', 'إنشاء روابط جديدة', 'urls'),
        ('url.edit', 'تعديل الروابط', 'urls'),
        ('url.delete', 'حذف الروابط', 'urls'),
        ('url.view_all', 'عرض جميع الروابط', 'urls'),
        ('url.restore', 'استعادة الروابط المحذوفة', 'urls'),
        
        # صلاحيات المستخدمين
        ('user.create', 'إنشاء مستخدمين جدد', 'users'),
        ('user.edit', 'تعديل بيانات المستخدمين', 'users'),
        ('user.delete', 'حذف المستخدمين', 'users'),
        ('user.view_all', 'عرض جميع المستخدمين', 'users'),
        ('user.restore', 'استعادة المستخدمين المحذوفين', 'users'),
        ('user.change_role', 'تغيير أدوار المستخدمين', 'users'),
        
        # صلاحيات الأدوار
        ('role.create', 'إنشاء أدوار جديدة', 'roles'),
        ('role.edit', 'تعديل الأدوار', 'roles'),
        ('role.delete', 'حذف الأدوار', 'roles'),
        ('role.view_all', 'عرض جميع الأدوار', 'roles'),
        ('role.assign', 'تعيين الأدوار للمستخدمين', 'roles'),
        
        # صلاحيات الأمان
        ('security.view', 'عرض معلومات الأمان', 'security'),
        ('security.manage', 'إدارة إعدادات الأمان', 'security'),
        ('audit.view', 'عرض سجلات المراجعة', 'security'),
        ('audit.manage', 'إدارة سجلات المراجعة', 'security'),
        
        # صلاحيات التحليلات
        ('analytics.view_own', 'عرض الإحصائيات الشخصية', 'analytics'),
        ('analytics.view_users', 'عرض إحصائيات المستخدمين', 'analytics'),
        ('analytics.view_trends', 'عرض تحليل الاتجاهات', 'analytics'),
        ('analytics.view_leaderboard', 'عرض لوحة المتصدرين', 'analytics'),
        ('analytics.compare_users', 'مقارنة أداء المستخدمين', 'analytics'),
        ('analytics.export', 'تصدير التقارير', 'analytics'),
        
        # صلاحيات النظام
        ('system.settings', 'إدارة إعدادات النظام', 'system'),
        ('system.backup', 'إنشاء نسخ احتياطية', 'system'),
        ('system.maintenance', 'صيانة النظام', 'system')
    ]
    
    for perm_name, perm_desc, category in permissions_data:
        permission = Permission.query.filter_by(name=perm_name).first()
        if not permission:
            permission = Permission(
                name=perm_name,
                display_name=perm_desc,
                description=perm_desc,
                category=category
            )
            db.session.add(permission)
    
    db.session.commit()
    
    # إنشاء مستخدم مدير افتراضي
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@rfah.me',
            password='Admin@123',
            full_name='مدير النظام',
            is_admin=True
        )
        db.session.add(admin_user)
    
    db.session.commit()
    print("تم إنشاء البيانات الأولية بنجاح")

if __name__ == '__main__':
    app = create_app()
    
    # تشغيل التطبيق
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 تم تشغيل نظام رفاه على المنفذ {port}")
    print(f"🌐 النطاق: {app.config['DOMAIN']}")
    print(f"🔗 الرابط: {app.config['BASE_URL']}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

