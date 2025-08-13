from flask import Blueprint, request, jsonify, session
from src.models.user import User, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'البريد الإلكتروني وكلمة المرور مطلوبان'}), 400
        
        # البحث عن المستخدم بالبريد الإلكتروني أو اسم المستخدم
        user = User.query.filter(
            (User.email == email) | (User.username == email)
        ).first()
        
        if not user:
            return jsonify({'error': 'بيانات تسجيل الدخول غير صحيحة'}), 401
        
        if not user.check_password(password):
            return jsonify({'error': 'بيانات تسجيل الدخول غير صحيحة'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'الحساب غير مفعل'}), 401
        
        # تحديث آخر تسجيل دخول
        user.update_last_login()
        
        # حفظ معلومات المستخدم في الجلسة
        session['user_id'] = user.id
        session['is_admin'] = user.is_admin
        
        return jsonify({
            'message': 'تم تسجيل الدخول بنجاح',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'message': 'تم تسجيل الخروج بنجاح'}), 200
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'غير مسجل الدخول'}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        is_admin = data.get('is_admin', False)
        
        if not all([username, email, password, full_name]):
            return jsonify({'error': 'جميع الحقول مطلوبة'}), 400
        
        # التحقق من عدم وجود المستخدم
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'البريد الإلكتروني موجود بالفعل'}), 400
        
        # إنشاء مستخدم جديد
        user = User(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            is_admin=is_admin
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء الحساب بنجاح',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

