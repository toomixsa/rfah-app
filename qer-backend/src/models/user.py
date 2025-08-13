from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # للتوافق مع النظام الحالي
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)  # للحذف الناعم
    
    # العلاقة مع الأدوار
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    
    # العلاقة مع الروابط المختصرة
    shortened_urls = db.relationship('ShortenedUrl', backref='user', lazy=True)

    def __init__(self, username, email, password, full_name, is_admin=False, 
                 phone=None, department=None, position=None, role_id=None):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.full_name = full_name
        self.is_admin = is_admin
        self.phone = phone
        self.department = department
        self.position = position
        self.role_id = role_id

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """تشفير وحفظ كلمة المرور"""
        self.password_hash = generate_password_hash(password)
    
    def has_permission(self, permission_name):
        """التحقق من وجود صلاحية معينة للمستخدم"""
        # المدير العام له جميع الصلاحيات
        if self.is_admin:
            return True
            
        if not self.role_obj or not self.role_obj.is_active:
            return False
        return self.role_obj.has_permission(permission_name)
    
    def get_permissions(self):
        """جلب جميع صلاحيات المستخدم"""
        if self.is_admin:
            # المدير العام له جميع الصلاحيات
            from src.models.role import Permission
            return [perm.name for perm in Permission.query.filter_by(is_active=True).all()]
            
        if not self.role_obj or not self.role_obj.is_active:
            return []
        return [perm.name for perm in self.role_obj.permissions if perm.is_active]
    
    def soft_delete(self):
        """الحذف الناعم للمستخدم"""
        self.deleted_at = datetime.utcnow()
        self.is_active = False
    
    def restore(self):
        """استعادة المستخدم المحذوف"""
        self.deleted_at = None
        self.is_active = True

    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self, include_role=False, include_permissions=False):
        result = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'department': self.department,
            'position': self.position,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'deleted_at': self.deleted_at.strftime('%Y-%m-%d %H:%M:%S') if self.deleted_at else None,
            'role_id': self.role_id,
            'urls_count': len([url for url in self.shortened_urls if not url.deleted_at])
        }
        
        if include_role and self.role_obj:
            result['role'] = self.role_obj.to_dict()
        
        if include_permissions:
            result['permissions'] = self.get_permissions()
        
        return result
    
    @staticmethod
    def get_active_users():
        """جلب جميع المستخدمين النشطين (غير المحذوفين)"""
        return User.query.filter_by(is_active=True, deleted_at=None).all()
    
    @staticmethod
    def get_deleted_users():
        """جلب جميع المستخدمين المحذوفين"""
        return User.query.filter(User.deleted_at.isnot(None)).all()
    
    @staticmethod
    def get_by_role(role_id):
        """جلب المستخدمين حسب الدور"""
        return User.query.filter_by(role_id=role_id, is_active=True, deleted_at=None).all()
