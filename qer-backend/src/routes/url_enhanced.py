from flask import Blueprint, request, jsonify, session, redirect
from src.models.user import db, User
from src.models.url import ShortenedUrl
from src.models.analytics import Analytics
from functools import wraps
from datetime import datetime
import validators

url_enhanced_bp = Blueprint('url_enhanced', __name__)

def require_login():
    """ديكوريتر للتحقق من تسجيل الدخول"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
            
            user = User.query.get(session['user_id'])
            if not user or not user.is_active or user.deleted_at:
                return jsonify({'error': 'المستخدم غير موجود أو غير نشط'}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

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

@url_enhanced_bp.route('/shorten', methods=['POST'])
@require_permission('urls.create')
def shorten_url():
    try:
        data = request.get_json()
        original_url = data.get('url') or data.get('original_url')
        custom_alias = data.get('custom_alias')
        title = data.get('title')
        description = data.get('description')
        expires_at = data.get('expires_at')
        
        if not original_url:
            return jsonify({'error': 'الرابط الأصلي مطلوب'}), 400
        
        # التحقق من صحة الرابط
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url
        
        if not validators.url(original_url):
            return jsonify({'error': 'الرابط غير صالح'}), 400
        
        # التحقق من الاسم المخصص إذا تم تقديمه
        if custom_alias:
            if len(custom_alias) < 3 or len(custom_alias) > 50:
                return jsonify({'error': 'الاسم المخصص يجب أن يكون بين 3 و 50 حرف'}), 400
            
            existing_url = ShortenedUrl.query.filter_by(short_code=custom_alias).first()
            if existing_url:
                return jsonify({'error': 'الاسم المخصص مستخدم بالفعل'}), 400
        
        # تحويل تاريخ انتهاء الصلاحية إذا تم تقديمه
        expires_datetime = None
        if expires_at:
            try:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'تنسيق تاريخ انتهاء الصلاحية غير صحيح'}), 400
        
        # إنشاء الرابط المختصر
        shortened_url = ShortenedUrl(
            original_url=original_url,
            custom_alias=custom_alias,
            user_id=session['user_id'],
            title=title,
            description=description,
            expires_at=expires_datetime
        )
        
        db.session.add(shortened_url)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الرابط المختصر بنجاح',
            'data': shortened_url.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في إنشاء الرابط المختصر: {str(e)}'}), 500

@url_enhanced_bp.route('/my-urls', methods=['GET'])
@require_permission('urls.view_own')
def get_my_urls():
    try:
        user_id = session['user_id']
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
        
        urls = ShortenedUrl.get_by_user(user_id, include_deleted=include_deleted)
        
        return jsonify({
            'success': True,
            'data': [url.to_dict(include_stats=True) for url in urls]
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الروابط: {str(e)}'}), 500

@url_enhanced_bp.route('/urls', methods=['GET'])
@require_permission('urls.view_all')
def get_all_urls():
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
            'data': [url.to_dict(include_stats=True) for url in urls]
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الروابط: {str(e)}'}), 500

@url_enhanced_bp.route('/urls/<int:url_id>', methods=['GET'])
@require_login()
def get_url_details(url_id):
    try:
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        user = User.query.get(session['user_id'])
        
        # التحقق من الصلاحيات
        if not user.has_permission('urls.view_all') and url.user_id != user.id:
            return jsonify({'error': 'ليس لديك صلاحية لعرض هذا الرابط'}), 403
        
        return jsonify({
            'success': True,
            'data': url.to_dict(include_stats=True)
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب تفاصيل الرابط: {str(e)}'}), 500

@url_enhanced_bp.route('/urls/<int:url_id>', methods=['PUT'])
@require_login()
def update_url(url_id):
    try:
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        user = User.query.get(session['user_id'])
        
        # التحقق من الصلاحيات
        can_edit = (user.has_permission('urls.edit_all') or 
                   (user.has_permission('urls.edit_own') and url.user_id == user.id))
        
        if not can_edit:
            return jsonify({'error': 'ليس لديك صلاحية لتعديل هذا الرابط'}), 403
        
        data = request.get_json()
        
        # تحديث البيانات
        if 'title' in data:
            url.title = data['title']
        if 'description' in data:
            url.description = data['description']
        if 'original_url' in data:
            original_url = data['original_url']
            if not original_url.startswith(('http://', 'https://')):
                original_url = 'https://' + original_url
            
            if not validators.url(original_url):
                return jsonify({'error': 'الرابط غير صالح'}), 400
            
            url.original_url = original_url
        
        # تحديث تاريخ انتهاء الصلاحية
        if 'expires_at' in data:
            expires_at = data['expires_at']
            if expires_at:
                try:
                    url.expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'error': 'تنسيق تاريخ انتهاء الصلاحية غير صحيح'}), 400
            else:
                url.expires_at = None
        
        # تحديث حالة النشاط
        if 'is_active' in data:
            url.is_active = data['is_active']
        
        url.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الرابط بنجاح',
            'data': url.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في تحديث الرابط: {str(e)}'}), 500

@url_enhanced_bp.route('/urls/<int:url_id>', methods=['DELETE'])
@require_login()
def delete_url(url_id):
    try:
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        user = User.query.get(session['user_id'])
        
        # التحقق من الصلاحيات
        can_delete = (user.has_permission('urls.delete_all') or 
                     (user.has_permission('urls.delete_own') and url.user_id == user.id))
        
        if not can_delete:
            return jsonify({'error': 'ليس لديك صلاحية لحذف هذا الرابط'}), 403
        
        url.soft_delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الرابط بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في حذف الرابط: {str(e)}'}), 500

@url_enhanced_bp.route('/urls/<int:url_id>/restore', methods=['POST'])
@require_permission('urls.delete_all')
def restore_url(url_id):
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
            'data': url.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ في استعادة الرابط: {str(e)}'}), 500

@url_enhanced_bp.route('/urls/<int:url_id>/stats', methods=['GET'])
@require_login()
def get_url_stats(url_id):
    try:
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        user = User.query.get(session['user_id'])
        
        # التحقق من الصلاحيات
        can_view_stats = (user.has_permission('reports.view_all') or 
                         (user.has_permission('reports.view_own') and url.user_id == user.id))
        
        if not can_view_stats:
            return jsonify({'error': 'ليس لديك صلاحية لعرض إحصائيات هذا الرابط'}), 403
        
        days = int(request.args.get('days', 30))
        stats = Analytics.get_url_detailed_stats(url_id, days)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات الرابط: {str(e)}'}), 500

@url_enhanced_bp.route('/my-stats', methods=['GET'])
@require_permission('reports.view_own')
def get_my_stats():
    try:
        user_id = session['user_id']
        days = int(request.args.get('days', 30))
        
        stats = Analytics.get_user_stats(user_id, days)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الإحصائيات: {str(e)}'}), 500

@url_enhanced_bp.route('/stats', methods=['GET'])
@require_permission('reports.view_all')
def get_system_stats():
    try:
        days = int(request.args.get('days', 30))
        stats = Analytics.get_system_stats(days)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات النظام: {str(e)}'}), 500

@url_enhanced_bp.route('/users-stats', methods=['GET'])
@require_permission('reports.view_all')
def get_users_stats():
    try:
        users = User.get_active_users()
        users_stats = []
        
        for user in users:
            user_urls = ShortenedUrl.get_by_user(user.id, include_deleted=False)
            total_urls = len(user_urls)
            total_clicks = sum(url.clicks for url in user_urls)
            avg_clicks = round(total_clicks / total_urls, 2) if total_urls > 0 else 0
            
            users_stats.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'department': user.department,
                'position': user.position,
                'is_admin': user.is_admin,
                'role_name': user.role_obj.display_name if user.role_obj else 'غير محدد',
                'total_urls': total_urls,
                'total_clicks': total_clicks,
                'avg_clicks': avg_clicks,
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'لم يسجل دخول',
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'success': True,
            'data': users_stats
        })
        
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات المستخدمين: {str(e)}'}), 500

# نقطة النهاية للتوجيه (الرابط المختصر)
@url_enhanced_bp.route('/<short_code>')
def redirect_url(short_code):
    try:
        url = ShortenedUrl.get_by_short_code(short_code)
        
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        # التحقق من انتهاء الصلاحية
        if url.is_expired():
            return jsonify({'error': 'انتهت صلاحية هذا الرابط'}), 410
        
        # تسجيل النقرة مع تفاصيل إضافية
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        referer = request.headers.get('Referer')
        
        url.increment_clicks(ip_address=ip_address, user_agent=user_agent, referer=referer)
        
        return redirect(url.original_url)
    
    except Exception as e:
        return jsonify({'error': f'خطأ في التوجيه: {str(e)}'}), 500

# نقطة نهاية للحصول على معلومات الرابط دون توجيه
@url_enhanced_bp.route('/<short_code>/info')
def get_url_info(short_code):
    try:
        url = ShortenedUrl.get_by_short_code(short_code)
        
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'short_code': url.short_code,
                'original_url': url.original_url,
                'title': url.title,
                'description': url.description,
                'clicks': url.clicks,
                'created_at': url.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_expired': url.is_expired(),
                'expires_at': url.expires_at.strftime('%Y-%m-%d %H:%M:%S') if url.expires_at else None
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب معلومات الرابط: {str(e)}'}), 500

