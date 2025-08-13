from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.role import Role, Permission, create_default_roles_and_permissions
from src.models.url import ShortenedUrl
from src.models.analytics import Analytics
from functools import wraps
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def require_permission(permission_name):
    """ديكوريتر للتحقق من الصلاحيات"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'غير مصرح لك بالوصول'}), 401
            
            user = User.query.get(session['user_id'])
            if not user or not user.is_active or user.deleted_at:
                return jsonify({'error': 'المستخدم غير موجود أو غير نشط'}), 401
            
            if not user.has_permission(permission_name):
                return jsonify({'error': 'ليس لديك صلاحية للوصول إلى هذه الوظيفة'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin():
    """ديكوريتر للتحقق من صلاحيات المدير"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'غير مصرح لك بالوصول'}), 401
            
            user = User.query.get(session['user_id'])
            if not user or not user.is_active or user.deleted_at:
                return jsonify({'error': 'المستخدم غير موجود أو غير نشط'}), 401
            
            if not user.is_admin and not user.has_permission('system.settings'):
                return jsonify({'error': 'ليس لديك صلاحية مدير النظام'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== إدارة الأدوار ====================

@admin_bp.route('/roles', methods=['GET'])
@require_permission('roles.view')
def get_roles():
    """جلب جميع الأدوار"""
    try:
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
        
        if include_deleted:
            roles = Role.query.all()
        else:
            roles = Role.get_active_roles()
        
        return jsonify({
            'success': True,
            'roles': [role.to_dict(include_permissions=True) for role in roles]
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الأدوار: {str(e)}'}), 500

@admin_bp.route('/roles', methods=['POST'])
@require_permission('roles.create')
def create_role():
    """إنشاء دور جديد"""
    try:
        data = request.get_json()
        
        # التحقق من البيانات المطلوبة
        if not data.get('name') or not data.get('display_name'):
            return jsonify({'error': 'اسم الدور والاسم المعروض مطلوبان'}), 400
        
        # التحقق من عدم وجود دور بنفس الاسم
        existing_role = Role.query.filter_by(name=data['name']).first()
        if existing_role:
            return jsonify({'error': 'يوجد دور بهذا الاسم مسبقاً'}), 400
        
        # إنشاء الدور الجديد
        role = Role(
            name=data['name'],
            display_name=data['display_name'],
            description=data.get('description', ''),
            is_system=False
        )
        
        db.session.add(role)
        db.session.flush()  # للحصول على ID
        
        # إضافة الصلاحيات المحددة
        permission_ids = data.get('permission_ids', [])
        for perm_id in permission_ids:
            permission = Permission.query.get(perm_id)
            if permission and permission.is_active:
                role.add_permission(permission)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الدور بنجاح',
            'role': role.to_dict(include_permissions=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في إنشاء الدور: {str(e)}'}), 500

@admin_bp.route('/roles/<int:role_id>', methods=['PUT'])
@require_permission('roles.edit')
def update_role(role_id):
    """تحديث دور موجود"""
    try:
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'الدور غير موجود'}), 404
        
        if role.is_system:
            return jsonify({'error': 'لا يمكن تعديل الأدوار النظامية'}), 400
        
        data = request.get_json()
        
        # تحديث البيانات الأساسية
        if 'display_name' in data:
            role.display_name = data['display_name']
        if 'description' in data:
            role.description = data['description']
        
        # تحديث الصلاحيات
        if 'permission_ids' in data:
            # إزالة جميع الصلاحيات الحالية
            role.permissions.clear()
            
            # إضافة الصلاحيات الجديدة
            permission_ids = data['permission_ids']
            for perm_id in permission_ids:
                permission = Permission.query.get(perm_id)
                if permission and permission.is_active:
                    role.add_permission(permission)
        
        role.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الدور بنجاح',
            'role': role.to_dict(include_permissions=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في تحديث الدور: {str(e)}'}), 500

@admin_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@require_permission('roles.delete')
def delete_role(role_id):
    """حذف دور (حذف ناعم)"""
    try:
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'الدور غير موجود'}), 404
        
        if role.is_system:
            return jsonify({'error': 'لا يمكن حذف الأدوار النظامية'}), 400
        
        # التحقق من عدم وجود مستخدمين مرتبطين بهذا الدور
        users_count = User.query.filter_by(role_id=role_id, is_active=True, deleted_at=None).count()
        if users_count > 0:
            return jsonify({'error': f'لا يمكن حذف الدور لأنه مرتبط بـ {users_count} مستخدم'}), 400
        
        role.soft_delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الدور بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في حذف الدور: {str(e)}'}), 500

@admin_bp.route('/roles/<int:role_id>/restore', methods=['POST'])
@require_permission('roles.restore')
def restore_role(role_id):
    """استعادة دور محذوف"""
    try:
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'الدور غير موجود'}), 404
        
        if not role.deleted_at:
            return jsonify({'error': 'الدور غير محذوف'}), 400
        
        role.restore()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم استعادة الدور بنجاح',
            'role': role.to_dict(include_permissions=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في استعادة الدور: {str(e)}'}), 500

# ==================== إدارة الصلاحيات ====================

@admin_bp.route('/permissions', methods=['GET'])
@require_permission('roles.view')
def get_permissions():
    """جلب جميع الصلاحيات مجمعة حسب التصنيف"""
    try:
        permissions_by_category = Permission.get_by_category()
        return jsonify({
            'success': True,
            'permissions': permissions_by_category
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الصلاحيات: {str(e)}'}), 500

# ==================== إدارة المستخدمين ====================

@admin_bp.route('/users', methods=['GET'])
@require_permission('users.view')
def get_users():
    """جلب جميع المستخدمين"""
    try:
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
        role_id = request.args.get('role_id')
        
        if include_deleted:
            users = User.query.all()
        elif role_id:
            users = User.get_by_role(int(role_id))
        else:
            users = User.get_active_users()
        
        return jsonify({
            'success': True,
            'users': [user.to_dict(include_role=True) for user in users]
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب المستخدمين: {str(e)}'}), 500

@admin_bp.route('/users', methods=['POST'])
@require_permission('users.create')
def create_user():
    """إنشاء مستخدم جديد"""
    try:
        data = request.get_json()
        
        # التحقق من البيانات المطلوبة
        required_fields = ['username', 'email', 'password', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'الحقل {field} مطلوب'}), 400
        
        # التحقق من عدم وجود مستخدم بنفس اسم المستخدم أو البريد الإلكتروني
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        if existing_user:
            return jsonify({'error': 'يوجد مستخدم بنفس اسم المستخدم أو البريد الإلكتروني'}), 400
        
        # التحقق من صحة الدور
        role_id = data.get('role_id')
        if role_id:
            role = Role.query.get(role_id)
            if not role or not role.is_active or role.deleted_at:
                return jsonify({'error': 'الدور المحدد غير صحيح'}), 400
        
        # إنشاء المستخدم الجديد
        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            full_name=data['full_name'],
            phone=data.get('phone'),
            department=data.get('department'),
            position=data.get('position'),
            role_id=role_id,
            is_admin=data.get('is_admin', False)
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء المستخدم بنجاح',
            'user': user.to_dict(include_role=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في إنشاء المستخدم: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_permission('users.edit')
def update_user(user_id):
    """تحديث مستخدم موجود"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        data = request.get_json()
        
        # تحديث البيانات الأساسية
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data and data['email'] != user.email:
            # التحقق من عدم وجود مستخدم آخر بنفس البريد الإلكتروني
            existing_user = User.query.filter(User.email == data['email'], User.id != user_id).first()
            if existing_user:
                return jsonify({'error': 'يوجد مستخدم آخر بنفس البريد الإلكتروني'}), 400
            user.email = data['email']
        
        if 'phone' in data:
            user.phone = data['phone']
        if 'department' in data:
            user.department = data['department']
        if 'position' in data:
            user.position = data['position']
        
        # تحديث كلمة المرور إذا تم تقديمها
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        # تحديث الدور
        if 'role_id' in data:
            role_id = data['role_id']
            if role_id:
                role = Role.query.get(role_id)
                if not role or not role.is_active or role.deleted_at:
                    return jsonify({'error': 'الدور المحدد غير صحيح'}), 400
            user.role_id = role_id
        
        # تحديث صلاحيات المدير (للمدراء فقط)
        current_user = User.query.get(session['user_id'])
        if current_user.is_admin and 'is_admin' in data:
            user.is_admin = data['is_admin']
        
        # تحديث حالة النشاط
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث المستخدم بنجاح',
            'user': user.to_dict(include_role=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في تحديث المستخدم: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_permission('users.delete')
def delete_user(user_id):
    """حذف مستخدم (حذف ناعم)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # منع حذف المدير الحالي لنفسه
        if user_id == session['user_id']:
            return jsonify({'error': 'لا يمكنك حذف حسابك الخاص'}), 400
        
        user.soft_delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف المستخدم بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في حذف المستخدم: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>/restore', methods=['POST'])
@require_permission('users.restore')
def restore_user(user_id):
    """استعادة مستخدم محذوف"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        if not user.deleted_at:
            return jsonify({'error': 'المستخدم غير محذوف'}), 400
        
        user.restore()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم استعادة المستخدم بنجاح',
            'user': user.to_dict(include_role=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في استعادة المستخدم: {str(e)}'}), 500

# ==================== إدارة الروابط ====================

@admin_bp.route('/urls', methods=['GET'])
@require_permission('urls.view_all')
def get_all_urls():
    """جلب جميع الروابط المختصرة"""
    try:
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
        user_id = request.args.get('user_id')
        
        if include_deleted:
            urls = ShortenedUrl.query.all()
        elif user_id:
            urls = ShortenedUrl.get_by_user(int(user_id), include_deleted=False)
        else:
            urls = ShortenedUrl.get_active_urls()
        
        return jsonify({
            'success': True,
            'urls': [url.to_dict(include_stats=True) for url in urls]
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الروابط: {str(e)}'}), 500

@admin_bp.route('/urls/<int:url_id>/restore', methods=['POST'])
@require_permission('urls.delete_all')
def restore_url(url_id):
    """استعادة رابط محذوف"""
    try:
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        if not url.deleted_at:
            return jsonify({'error': 'الرابط غير محذوف'}), 400
        
        url.restore()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم استعادة الرابط بنجاح',
            'url': url.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في استعادة الرابط: {str(e)}'}), 500

# ==================== التقارير والإحصائيات ====================

@admin_bp.route('/stats/system', methods=['GET'])
@require_permission('reports.view_all')
def get_system_stats():
    """جلب إحصائيات النظام العامة"""
    try:
        days = int(request.args.get('days', 30))
        stats = Analytics.get_system_stats(days)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات النظام: {str(e)}'}), 500

@admin_bp.route('/stats/user/<int:user_id>', methods=['GET'])
@require_permission('reports.view_all')
def get_user_stats(user_id):
    """جلب إحصائيات مستخدم محدد"""
    try:
        days = int(request.args.get('days', 30))
        stats = Analytics.get_user_stats(user_id, days)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات المستخدم: {str(e)}'}), 500

@admin_bp.route('/stats/url/<int:url_id>', methods=['GET'])
@require_permission('reports.view_all')
def get_url_stats(url_id):
    """جلب إحصائيات رابط محدد"""
    try:
        days = int(request.args.get('days', 30))
        stats = Analytics.get_url_detailed_stats(url_id, days)
        
        if not stats:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات الرابط: {str(e)}'}), 500

# ==================== إعدادات النظام ====================

@admin_bp.route('/system/init', methods=['POST'])
@require_admin()
def initialize_system():
    """تهيئة النظام بالأدوار والصلاحيات الافتراضية"""
    try:
        create_default_roles_and_permissions()
        
        return jsonify({
            'success': True,
            'message': 'تم تهيئة النظام بنجاح'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في تهيئة النظام: {str(e)}'}), 500

@admin_bp.route('/system/info', methods=['GET'])
@require_admin()
def get_system_info():
    """جلب معلومات النظام"""
    try:
        total_users = User.query.filter_by(is_active=True, deleted_at=None).count()
        total_roles = Role.query.filter_by(is_active=True, deleted_at=None).count()
        total_permissions = Permission.query.filter_by(is_active=True).count()
        total_urls = ShortenedUrl.query.filter_by(is_active=True, deleted_at=None).count()
        
        return jsonify({
            'success': True,
            'system_info': {
                'total_users': total_users,
                'total_roles': total_roles,
                'total_permissions': total_permissions,
                'total_urls': total_urls,
                'version': '2.0.0',
                'domain': 'rfah.me'
            }
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب معلومات النظام: {str(e)}'}), 500

