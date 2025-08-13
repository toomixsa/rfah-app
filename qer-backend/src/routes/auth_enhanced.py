from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.role import create_default_roles_and_permissions

auth_enhanced_bp = Blueprint('auth_enhanced', __name__)

@auth_enhanced_bp.route('/register', methods=['POST'])
def register():
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
        
        # إنشاء المستخدم الجديد
        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            full_name=data['full_name'],
            phone=data.get('phone'),
            department=data.get('department'),
            position=data.get('position')
        )
        
        # إذا كان هذا أول مستخدم، اجعله مدير عام
        if User.query.count() == 0:
            user.is_admin = True
            # تهيئة النظام بالأدوار والصلاحيات الافتراضية
            db.session.add(user)
            db.session.commit()
            create_default_roles_and_permissions()
        else:
            # تعيين دور الموظف الافتراضي للمستخدمين الجدد
            from src.models.role import Role
            employee_role = Role.query.filter_by(name='employee').first()
            if employee_role:
                user.role_id = employee_role.id
            
            db.session.add(user)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الحساب بنجاح',
            'user': user.to_dict(include_role=True, include_permissions=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في إنشاء الحساب: {str(e)}'}), 500

@auth_enhanced_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'اسم المستخدم وكلمة المرور مطلوبان'}), 400
        
        # البحث عن المستخدم بالبريد الإلكتروني أو اسم المستخدم
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401
        
        # التحقق من حالة المستخدم
        if not user.is_active or user.deleted_at:
            return jsonify({'error': 'الحساب غير نشط أو محذوف'}), 401
        
        # تحديث وقت آخر تسجيل دخول
        user.update_last_login()
        
        # حفظ معلومات المستخدم في الجلسة
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الدخول بنجاح',
            'user': user.to_dict(include_role=True, include_permissions=True)
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في تسجيل الدخول: {str(e)}'}), 500

@auth_enhanced_bp.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الخروج بنجاح'
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في تسجيل الخروج: {str(e)}'}), 500

@auth_enhanced_bp.route('/profile', methods=['GET'])
def get_profile():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'غير مصرح لك بالوصول'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_active or user.deleted_at:
            return jsonify({'error': 'المستخدم غير موجود أو غير نشط'}), 401
        
        return jsonify({
            'success': True,
            'user': user.to_dict(include_role=True, include_permissions=True)
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الملف الشخصي: {str(e)}'}), 500

@auth_enhanced_bp.route('/profile', methods=['PUT'])
def update_profile():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'غير مصرح لك بالوصول'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_active or user.deleted_at:
            return jsonify({'error': 'المستخدم غير موجود أو غير نشط'}), 401
        
        data = request.get_json()
        
        # تحديث البيانات الأساسية
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data and data['email'] != user.email:
            # التحقق من عدم وجود مستخدم آخر بنفس البريد الإلكتروني
            existing_user = User.query.filter(User.email == data['email'], User.id != user.id).first()
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
        if 'current_password' in data and 'new_password' in data:
            if not user.check_password(data['current_password']):
                return jsonify({'error': 'كلمة المرور الحالية غير صحيحة'}), 400
            user.set_password(data['new_password'])
        
        from datetime import datetime
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الملف الشخصي بنجاح',
            'user': user.to_dict(include_role=True, include_permissions=True)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في تحديث الملف الشخصي: {str(e)}'}), 500

@auth_enhanced_bp.route('/check-session', methods=['GET'])
def check_session():
    """التحقق من صحة الجلسة"""
    try:
        if 'user_id' not in session:
            return jsonify({'authenticated': False}), 200
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_active or user.deleted_at:
            session.clear()
            return jsonify({'authenticated': False}), 200
        
        return jsonify({
            'authenticated': True,
            'user': user.to_dict(include_role=True, include_permissions=True)
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في التحقق من الجلسة: {str(e)}'}), 500

