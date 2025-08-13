from src.models.user import db
from datetime import datetime

# جدول الربط بين الأدوار والصلاحيات (Many-to-Many)
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # للأدوار النظامية التي لا يمكن حذفها
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # للحذف الناعم
    
    # العلاقات
    users = db.relationship('User', backref='role_obj', lazy=True)
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                                backref=db.backref('roles', lazy=True))
    
    def __init__(self, name, display_name, description=None, is_system=False):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.is_system = is_system
    
    def has_permission(self, permission_name):
        """التحقق من وجود صلاحية معينة في هذا الدور"""
        return any(perm.name == permission_name for perm in self.permissions if perm.is_active)
    
    def add_permission(self, permission):
        """إضافة صلاحية إلى الدور"""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission):
        """إزالة صلاحية من الدور"""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def soft_delete(self):
        """الحذف الناعم للدور"""
        if not self.is_system:
            self.deleted_at = datetime.utcnow()
            self.is_active = False
    
    def restore(self):
        """استعادة الدور المحذوف"""
        self.deleted_at = None
        self.is_active = True
    
    def to_dict(self, include_permissions=False):
        result = {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'deleted_at': self.deleted_at.strftime('%Y-%m-%d %H:%M:%S') if self.deleted_at else None,
            'users_count': len([u for u in self.users if u.is_active and not u.deleted_at])
        }
        
        if include_permissions:
            result['permissions'] = [perm.to_dict() for perm in self.permissions if perm.is_active]
        
        return result
    
    @staticmethod
    def get_active_roles():
        """جلب جميع الأدوار النشطة (غير المحذوفة)"""
        return Role.query.filter_by(is_active=True, deleted_at=None).all()
    
    @staticmethod
    def get_deleted_roles():
        """جلب جميع الأدوار المحذوفة"""
        return Role.query.filter(Role.deleted_at.isnot(None)).all()


class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # تصنيف الصلاحية (مثل: users, urls, reports)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # للصلاحيات النظامية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, name, display_name, category, description=None, is_system=False):
        self.name = name
        self.display_name = display_name
        self.category = category
        self.description = description
        self.is_system = is_system
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
    
    @staticmethod
    def get_by_category():
        """جلب الصلاحيات مجمعة حسب التصنيف"""
        permissions = Permission.query.filter_by(is_active=True).all()
        categories = {}
        for perm in permissions:
            if perm.category not in categories:
                categories[perm.category] = []
            categories[perm.category].append(perm.to_dict())
        return categories


def create_default_roles_and_permissions():
    """إنشاء الأدوار والصلاحيات الافتراضية"""
    
    # إنشاء الصلاحيات الافتراضية
    default_permissions = [
        # صلاحيات إدارة المستخدمين
        ('users.view', 'عرض المستخدمين', 'users', 'عرض قائمة المستخدمين ومعلوماتهم'),
        ('users.create', 'إضافة مستخدمين', 'users', 'إضافة مستخدمين جدد'),
        ('users.edit', 'تعديل المستخدمين', 'users', 'تعديل معلومات المستخدمين'),
        ('users.delete', 'حذف المستخدمين', 'users', 'حذف المستخدمين'),
        ('users.restore', 'استعادة المستخدمين', 'users', 'استعادة المستخدمين المحذوفين'),
        
        # صلاحيات إدارة الروابط
        ('urls.view_all', 'عرض جميع الروابط', 'urls', 'عرض جميع الروابط المختصرة'),
        ('urls.view_own', 'عرض الروابط الخاصة', 'urls', 'عرض الروابط الخاصة بالمستخدم فقط'),
        ('urls.create', 'إنشاء روابط', 'urls', 'إنشاء روابط مختصرة جديدة'),
        ('urls.edit_all', 'تعديل جميع الروابط', 'urls', 'تعديل جميع الروابط المختصرة'),
        ('urls.edit_own', 'تعديل الروابط الخاصة', 'urls', 'تعديل الروابط الخاصة بالمستخدم فقط'),
        ('urls.delete_all', 'حذف جميع الروابط', 'urls', 'حذف جميع الروابط المختصرة'),
        ('urls.delete_own', 'حذف الروابط الخاصة', 'urls', 'حذف الروابط الخاصة بالمستخدم فقط'),
        
        # صلاحيات إدارة الأدوار
        ('roles.view', 'عرض الأدوار', 'roles', 'عرض قائمة الأدوار والصلاحيات'),
        ('roles.create', 'إضافة أدوار', 'roles', 'إضافة أدوار جديدة'),
        ('roles.edit', 'تعديل الأدوار', 'roles', 'تعديل الأدوار والصلاحيات'),
        ('roles.delete', 'حذف الأدوار', 'roles', 'حذف الأدوار'),
        ('roles.restore', 'استعادة الأدوار', 'roles', 'استعادة الأدوار المحذوفة'),
        
        # صلاحيات التقارير والإحصائيات
        ('reports.view_all', 'عرض جميع التقارير', 'reports', 'عرض تقارير وإحصائيات جميع المستخدمين'),
        ('reports.view_own', 'عرض التقارير الخاصة', 'reports', 'عرض التقارير والإحصائيات الخاصة بالمستخدم'),
        ('reports.export', 'تصدير التقارير', 'reports', 'تصدير التقارير والإحصائيات'),
        
        # صلاحيات النظام
        ('system.settings', 'إعدادات النظام', 'system', 'الوصول إلى إعدادات النظام العامة'),
        ('system.logs', 'سجلات النظام', 'system', 'عرض سجلات النظام والأنشطة'),
        ('system.backup', 'النسخ الاحتياطي', 'system', 'إنشاء واستعادة النسخ الاحتياطية'),
    ]
    
    # إضافة الصلاحيات إلى قاعدة البيانات
    for perm_name, display_name, category, description in default_permissions:
        existing_perm = Permission.query.filter_by(name=perm_name).first()
        if not existing_perm:
            permission = Permission(
                name=perm_name,
                display_name=display_name,
                category=category,
                description=description,
                is_system=True
            )
            db.session.add(permission)
    
    # إنشاء الأدوار الافتراضية
    
    # دور المدير العام (Super Admin)
    super_admin_role = Role.query.filter_by(name='super_admin').first()
    if not super_admin_role:
        super_admin_role = Role(
            name='super_admin',
            display_name='مدير عام',
            description='مدير عام للنظام مع جميع الصلاحيات',
            is_system=True
        )
        db.session.add(super_admin_role)
        db.session.flush()  # للحصول على ID
        
        # إضافة جميع الصلاحيات للمدير العام
        all_permissions = Permission.query.all()
        for permission in all_permissions:
            super_admin_role.add_permission(permission)
    
    # دور المدير (Admin)
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(
            name='admin',
            display_name='مدير',
            description='مدير النظام مع صلاحيات إدارية',
            is_system=True
        )
        db.session.add(admin_role)
        db.session.flush()
        
        # إضافة صلاحيات محددة للمدير
        admin_permissions = [
            'users.view', 'users.create', 'users.edit',
            'urls.view_all', 'urls.create', 'urls.edit_all', 'urls.delete_all',
            'reports.view_all', 'reports.export',
            'system.logs'
        ]
        for perm_name in admin_permissions:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                admin_role.add_permission(permission)
    
    # دور الموظف (Employee)
    employee_role = Role.query.filter_by(name='employee').first()
    if not employee_role:
        employee_role = Role(
            name='employee',
            display_name='موظف',
            description='موظف عادي مع صلاحيات محدودة',
            is_system=True
        )
        db.session.add(employee_role)
        db.session.flush()
        
        # إضافة صلاحيات محددة للموظف
        employee_permissions = [
            'urls.view_own', 'urls.create', 'urls.edit_own', 'urls.delete_own',
            'reports.view_own'
        ]
        for perm_name in employee_permissions:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                employee_role.add_permission(permission)
    
    # دور المشاهد (Viewer)
    viewer_role = Role.query.filter_by(name='viewer').first()
    if not viewer_role:
        viewer_role = Role(
            name='viewer',
            display_name='مشاهد',
            description='مشاهد فقط مع صلاحيات محدودة جداً',
            is_system=True
        )
        db.session.add(viewer_role)
        db.session.flush()
        
        # إضافة صلاحيات محددة للمشاهد
        viewer_permissions = [
            'urls.view_own',
            'reports.view_own'
        ]
        for perm_name in viewer_permissions:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                viewer_role.add_permission(permission)
    
    db.session.commit()
    return super_admin_role, admin_role, employee_role, viewer_role

