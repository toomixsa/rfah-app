from flask import Blueprint, request, jsonify, redirect, session
from src.models.url import ShortenedUrl, db
from src.models.user import User
import validators

url_bp = Blueprint('url', __name__)

@url_bp.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        data = request.get_json()
        original_url = data.get('original_url')
        custom_alias = data.get('custom_alias', '').strip()
        
        # الحصول على معرف المستخدم من الجلسة
        user_id = session.get('user_id')
        
        if not original_url:
            return jsonify({'error': 'الرابط الأصلي مطلوب'}), 400
        
        # التحقق من صحة الرابط
        if not validators.url(original_url):
            return jsonify({'error': 'الرابط غير صالح'}), 400
        
        # التحقق من الاسم المخصص إذا تم توفيره
        if custom_alias:
            if len(custom_alias) < 3 or len(custom_alias) > 50:
                return jsonify({'error': 'الاسم المخصص يجب أن يكون بين 3 و 50 حرف'}), 400
            
            if ShortenedUrl.query.filter_by(short_code=custom_alias).first():
                return jsonify({'error': 'الاسم المخصص مستخدم بالفعل'}), 400
        
        # إنشاء رابط مختصر جديد
        shortened_url = ShortenedUrl(
            original_url=original_url,
            custom_alias=custom_alias if custom_alias else None,
            user_id=user_id
        )
        
        db.session.add(shortened_url)
        db.session.commit()
        
        return jsonify({
            'message': 'تم اختصار الرابط بنجاح',
            'data': shortened_url.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@url_bp.route('/urls', methods=['GET'])
def get_urls():
    try:
        user_id = request.args.get('user_id')
        current_user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # إذا لم يكن المستخدم مسجل الدخول
        if not current_user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        # إذا طلب المستخدم روابط مستخدم آخر وليس مسؤولاً
        if user_id and int(user_id) != current_user_id and not is_admin:
            return jsonify({'error': 'غير مسموح بعرض روابط المستخدمين الآخرين'}), 403
        
        # تحديد المستخدم المطلوب عرض روابطه
        target_user_id = user_id if user_id else current_user_id
        
        # جلب الروابط
        if is_admin and not user_id:
            # المسؤول يرى جميع الروابط إذا لم يحدد مستخدماً معيناً
            urls = ShortenedUrl.query.order_by(ShortenedUrl.created_at.desc()).all()
        else:
            # جلب روابط المستخدم المحدد
            urls = ShortenedUrl.query.filter_by(user_id=target_user_id).order_by(ShortenedUrl.created_at.desc()).all()
        
        return jsonify({
            'data': [url.to_dict() for url in urls]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@url_bp.route('/stats', methods=['GET'])
def get_stats():
    try:
        user_id = request.args.get('user_id')
        current_user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # إذا لم يكن المستخدم مسجل الدخول
        if not current_user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        # إذا طلب المستخدم إحصائيات مستخدم آخر وليس مسؤولاً
        if user_id and int(user_id) != current_user_id and not is_admin:
            return jsonify({'error': 'غير مسموح بعرض إحصائيات المستخدمين الآخرين'}), 403
        
        # تحديد المستخدم المطلوب عرض إحصائياته
        target_user_id = user_id if user_id else current_user_id
        
        # جلب الإحصائيات
        if is_admin and not user_id:
            # المسؤول يرى إحصائيات جميع المستخدمين
            urls = ShortenedUrl.query.all()
        else:
            # جلب إحصائيات المستخدم المحدد
            urls = ShortenedUrl.query.filter_by(user_id=target_user_id).all()
        
        total_urls = len(urls)
        total_clicks = sum(url.clicks for url in urls)
        avg_clicks = round(total_clicks / total_urls, 2) if total_urls > 0 else 0
        
        return jsonify({
            'data': {
                'total_urls': total_urls,
                'total_clicks': total_clicks,
                'avg_clicks': avg_clicks
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@url_bp.route('/users-stats', methods=['GET'])
def get_users_stats():
    try:
        current_user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # التحقق من أن المستخدم مسؤول
        if not current_user_id or not is_admin:
            return jsonify({'error': 'غير مسموح - يجب أن تكون مسؤولاً'}), 403
        
        # جلب جميع المستخدمين مع إحصائياتهم
        users = User.query.filter_by(is_active=True).all()
        users_stats = []
        
        for user in users:
            user_urls = ShortenedUrl.query.filter_by(user_id=user.id).all()
            total_urls = len(user_urls)
            total_clicks = sum(url.clicks for url in user_urls)
            avg_clicks = round(total_clicks / total_urls, 2) if total_urls > 0 else 0
            
            users_stats.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'is_admin': user.is_admin,
                'total_urls': total_urls,
                'total_clicks': total_clicks,
                'avg_clicks': avg_clicks,
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'لم يسجل دخول',
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'data': users_stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@url_bp.route('/delete/<int:url_id>', methods=['DELETE'])
def delete_url(url_id):
    try:
        current_user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        if not current_user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        # جلب الرابط
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        # التحقق من الصلاحيات
        if not is_admin and url.user_id != current_user_id:
            return jsonify({'error': 'غير مسموح - يمكن للمسؤولين فقط حذف روابط المستخدمين الآخرين'}), 403
        
        # حذف الرابط
        db.session.delete(url)
        db.session.commit()
        
        return jsonify({'message': 'تم حذف الرابط بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

@url_bp.route('/<short_code>')
def redirect_url(short_code):
    try:
        url = ShortenedUrl.get_by_short_code(short_code)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        # زيادة عدد النقرات
        url.clicks += 1
        db.session.commit()
        
        return redirect(url.original_url)
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ: {str(e)}'}), 500

