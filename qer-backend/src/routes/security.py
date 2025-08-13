"""
نقاط النهاية للأمان والمراجعة
"""

from flask import Blueprint, request, jsonify, session
from src.security import SecurityManager, AuditLogger, AuditEventType, AuditSeverity, require_auth, require_permission
from src.models.user import User, db
from datetime import datetime, timedelta

security_bp = Blueprint('security', __name__)

@security_bp.route('/audit-logs', methods=['GET'])
@require_auth
@require_permission('audit.view')
def get_audit_logs():
    """الحصول على سجلات المراجعة"""
    try:
        audit_logger = current_app.extensions.get('audit_logger')
        if not audit_logger:
            return jsonify({'error': 'نظام المراجعة غير متاح'}), 500
        
        # معاملات التصفية
        filters = {}
        
        if request.args.get('event_type'):
            filters['event_type'] = request.args.get('event_type')
        
        if request.args.get('user_id'):
            filters['user_id'] = int(request.args.get('user_id'))
        
        if request.args.get('severity'):
            filters['severity'] = request.args.get('severity')
        
        if request.args.get('start_date'):
            filters['start_date'] = datetime.fromisoformat(request.args.get('start_date'))
        
        if request.args.get('end_date'):
            filters['end_date'] = datetime.fromisoformat(request.args.get('end_date'))
        
        if request.args.get('ip_address'):
            filters['ip_address'] = request.args.get('ip_address')
        
        if request.args.get('resource_type'):
            filters['resource_type'] = request.args.get('resource_type')
        
        if request.args.get('success') is not None:
            filters['success'] = request.args.get('success').lower() == 'true'
        
        # معاملات التصفح
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)  # حد أقصى 100
        
        # الحصول على السجلات
        result = audit_logger.get_audit_logs(filters, page, per_page)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب سجلات المراجعة: {str(e)}'}), 500

@security_bp.route('/audit-statistics', methods=['GET'])
@require_auth
@require_permission('audit.view')
def get_audit_statistics():
    """الحصول على إحصائيات المراجعة"""
    try:
        audit_logger = current_app.extensions.get('audit_logger')
        if not audit_logger:
            return jsonify({'error': 'نظام المراجعة غير متاح'}), 500
        
        days = int(request.args.get('days', 30))
        days = min(days, 365)  # حد أقصى سنة واحدة
        
        statistics = audit_logger.get_audit_statistics(days)
        
        return jsonify({
            'success': True,
            'data': statistics
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات المراجعة: {str(e)}'}), 500

@security_bp.route('/security-status', methods=['GET'])
@require_auth
@require_permission('security.view')
def get_security_status():
    """الحصول على حالة الأمان العامة"""
    try:
        security_manager = current_app.extensions.get('security_manager')
        audit_logger = current_app.extensions.get('audit_logger')
        
        if not security_manager or not audit_logger:
            return jsonify({'error': 'أنظمة الأمان غير متاحة'}), 500
        
        # إحصائيات الأمان للأسبوع الماضي
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # عدد محاولات تسجيل الدخول الفاشلة
        failed_logins = audit_logger.get_audit_logs({
            'event_type': AuditEventType.LOGIN_FAILED.value,
            'start_date': week_ago,
            'success': False
        }, per_page=1000)
        
        # عدد الانتهاكات الأمنية
        security_violations = audit_logger.get_audit_logs({
            'event_type': AuditEventType.SECURITY_VIOLATION.value,
            'start_date': week_ago
        }, per_page=1000)
        
        # عدد الأنشطة المشبوهة
        suspicious_activities = audit_logger.get_audit_logs({
            'event_type': AuditEventType.SUSPICIOUS_ACTIVITY.value,
            'start_date': week_ago
        }, per_page=1000)
        
        # عدد عناوين IP المحظورة
        blocked_ips_count = len(security_manager.blocked_ips)
        
        # أكثر عناوين IP نشاطاً
        top_ips = {}
        for ip, attempts in security_manager.failed_attempts.items():
            recent_attempts = [
                attempt for attempt in attempts
                if time.time() - attempt < 604800  # أسبوع واحد
            ]
            if recent_attempts:
                top_ips[ip] = len(recent_attempts)
        
        top_ips = sorted(top_ips.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # تقييم مستوى الأمان
        security_score = 100
        
        if failed_logins['total'] > 50:
            security_score -= 20
        elif failed_logins['total'] > 20:
            security_score -= 10
        
        if security_violations['total'] > 0:
            security_score -= 30
        
        if suspicious_activities['total'] > 10:
            security_score -= 15
        
        if blocked_ips_count > 10:
            security_score -= 10
        
        security_level = 'عالي'
        if security_score < 70:
            security_level = 'متوسط'
        if security_score < 50:
            security_level = 'منخفض'
        
        return jsonify({
            'success': True,
            'data': {
                'security_score': max(security_score, 0),
                'security_level': security_level,
                'failed_logins_count': failed_logins['total'],
                'security_violations_count': security_violations['total'],
                'suspicious_activities_count': suspicious_activities['total'],
                'blocked_ips_count': blocked_ips_count,
                'top_suspicious_ips': [{'ip': ip, 'attempts': count} for ip, count in top_ips],
                'last_updated': datetime.utcnow().isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب حالة الأمان: {str(e)}'}), 500

@security_bp.route('/block-ip', methods=['POST'])
@require_auth
@require_permission('security.manage')
def block_ip():
    """حظر عنوان IP"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        reason = data.get('reason', 'حظر يدوي من المدير')
        
        if not ip_address:
            return jsonify({'error': 'عنوان IP مطلوب'}), 400
        
        security_manager = current_app.extensions.get('security_manager')
        audit_logger = current_app.extensions.get('audit_logger')
        
        if not security_manager:
            return jsonify({'error': 'نظام الأمان غير متاح'}), 500
        
        # إضافة IP إلى قائمة المحظورين
        security_manager.blocked_ips.add(ip_address)
        
        # تسجيل الحدث
        if audit_logger:
            audit_logger.log_event(
                AuditEventType.IP_BLOCKED,
                severity=AuditSeverity.HIGH.value,
                user_id=session.get('user_id'),
                additional_data={
                    'blocked_ip': ip_address,
                    'reason': reason,
                    'blocked_by': 'admin'
                }
            )
        
        return jsonify({
            'success': True,
            'message': f'تم حظر عنوان IP {ip_address} بنجاح'
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في حظر عنوان IP: {str(e)}'}), 500

@security_bp.route('/unblock-ip', methods=['POST'])
@require_auth
@require_permission('security.manage')
def unblock_ip():
    """إلغاء حظر عنوان IP"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        
        if not ip_address:
            return jsonify({'error': 'عنوان IP مطلوب'}), 400
        
        security_manager = current_app.extensions.get('security_manager')
        audit_logger = current_app.extensions.get('audit_logger')
        
        if not security_manager:
            return jsonify({'error': 'نظام الأمان غير متاح'}), 500
        
        # إزالة IP من قائمة المحظورين
        security_manager.blocked_ips.discard(ip_address)
        
        # مسح محاولات تسجيل الدخول الفاشلة
        if ip_address in security_manager.failed_attempts:
            del security_manager.failed_attempts[ip_address]
        
        # تسجيل الحدث
        if audit_logger:
            audit_logger.log_event(
                AuditEventType.IP_BLOCKED,  # نفس النوع مع تفاصيل مختلفة
                severity=AuditSeverity.MEDIUM.value,
                user_id=session.get('user_id'),
                additional_data={
                    'unblocked_ip': ip_address,
                    'action': 'unblock',
                    'unblocked_by': 'admin'
                }
            )
        
        return jsonify({
            'success': True,
            'message': f'تم إلغاء حظر عنوان IP {ip_address} بنجاح'
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في إلغاء حظر عنوان IP: {str(e)}'}), 500

@security_bp.route('/blocked-ips', methods=['GET'])
@require_auth
@require_permission('security.view')
def get_blocked_ips():
    """الحصول على قائمة عناوين IP المحظورة"""
    try:
        security_manager = current_app.extensions.get('security_manager')
        
        if not security_manager:
            return jsonify({'error': 'نظام الأمان غير متاح'}), 500
        
        blocked_ips = list(security_manager.blocked_ips)
        
        # إضافة معلومات إضافية لكل IP
        ip_details = []
        for ip in blocked_ips:
            failed_attempts = security_manager.failed_attempts.get(ip, [])
            recent_attempts = [
                attempt for attempt in failed_attempts
                if time.time() - attempt < 86400  # آخر 24 ساعة
            ]
            
            ip_details.append({
                'ip_address': ip,
                'failed_attempts_24h': len(recent_attempts),
                'total_failed_attempts': len(failed_attempts),
                'last_attempt': datetime.fromtimestamp(max(failed_attempts)).isoformat() if failed_attempts else None
            })
        
        return jsonify({
            'success': True,
            'data': {
                'blocked_ips': ip_details,
                'total_count': len(blocked_ips)
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب عناوين IP المحظورة: {str(e)}'}), 500

@security_bp.route('/cleanup-audit-logs', methods=['POST'])
@require_auth
@require_permission('audit.manage')
def cleanup_audit_logs():
    """تنظيف سجلات المراجعة القديمة"""
    try:
        data = request.get_json()
        days_to_keep = data.get('days_to_keep', 365)
        
        # التحقق من صحة القيمة
        if not isinstance(days_to_keep, int) or days_to_keep < 30:
            return jsonify({'error': 'يجب الاحتفاظ بالسجلات لمدة 30 يوم على الأقل'}), 400
        
        audit_logger = current_app.extensions.get('audit_logger')
        if not audit_logger:
            return jsonify({'error': 'نظام المراجعة غير متاح'}), 500
        
        deleted_count = audit_logger.cleanup_old_logs(days_to_keep)
        
        # تسجيل عملية التنظيف
        audit_logger.log_event(
            AuditEventType.SYSTEM_CONFIG_CHANGED,
            severity=AuditSeverity.MEDIUM.value,
            user_id=session.get('user_id'),
            additional_data={
                'action': 'cleanup_audit_logs',
                'days_to_keep': days_to_keep,
                'deleted_count': deleted_count
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'تم حذف {deleted_count} سجل قديم بنجاح',
            'deleted_count': deleted_count
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في تنظيف سجلات المراجعة: {str(e)}'}), 500

@security_bp.route('/security-settings', methods=['GET'])
@require_auth
@require_permission('security.view')
def get_security_settings():
    """الحصول على إعدادات الأمان"""
    try:
        from flask import current_app
        
        settings = {
            'max_login_attempts': current_app.config.get('MAX_LOGIN_ATTEMPTS', 5),
            'lockout_duration': current_app.config.get('LOCKOUT_DURATION', 900),
            'rate_limit_requests': current_app.config.get('RATE_LIMIT_REQUESTS', 100),
            'rate_limit_window': current_app.config.get('RATE_LIMIT_WINDOW', 3600),
            'password_min_length': current_app.config.get('PASSWORD_MIN_LENGTH', 8),
            'require_strong_password': current_app.config.get('REQUIRE_STRONG_PASSWORD', True),
            'jwt_access_token_expires': str(current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))),
            'jwt_refresh_token_expires': str(current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30)))
        }
        
        return jsonify({
            'success': True,
            'data': settings
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إعدادات الأمان: {str(e)}'}), 500

@security_bp.route('/security-settings', methods=['PUT'])
@require_auth
@require_permission('security.manage')
def update_security_settings():
    """تحديث إعدادات الأمان"""
    try:
        from flask import current_app
        
        data = request.get_json()
        audit_logger = current_app.extensions.get('audit_logger')
        
        # الإعدادات القديمة للمقارنة
        old_settings = {
            'max_login_attempts': current_app.config.get('MAX_LOGIN_ATTEMPTS'),
            'lockout_duration': current_app.config.get('LOCKOUT_DURATION'),
            'rate_limit_requests': current_app.config.get('RATE_LIMIT_REQUESTS'),
            'rate_limit_window': current_app.config.get('RATE_LIMIT_WINDOW'),
            'password_min_length': current_app.config.get('PASSWORD_MIN_LENGTH'),
            'require_strong_password': current_app.config.get('REQUIRE_STRONG_PASSWORD')
        }
        
        # تحديث الإعدادات
        new_settings = {}
        
        if 'max_login_attempts' in data:
            value = int(data['max_login_attempts'])
            if 1 <= value <= 20:
                current_app.config['MAX_LOGIN_ATTEMPTS'] = value
                new_settings['max_login_attempts'] = value
        
        if 'lockout_duration' in data:
            value = int(data['lockout_duration'])
            if 60 <= value <= 86400:  # من دقيقة إلى يوم
                current_app.config['LOCKOUT_DURATION'] = value
                new_settings['lockout_duration'] = value
        
        if 'rate_limit_requests' in data:
            value = int(data['rate_limit_requests'])
            if 10 <= value <= 1000:
                current_app.config['RATE_LIMIT_REQUESTS'] = value
                new_settings['rate_limit_requests'] = value
        
        if 'rate_limit_window' in data:
            value = int(data['rate_limit_window'])
            if 60 <= value <= 86400:  # من دقيقة إلى يوم
                current_app.config['RATE_LIMIT_WINDOW'] = value
                new_settings['rate_limit_window'] = value
        
        if 'password_min_length' in data:
            value = int(data['password_min_length'])
            if 6 <= value <= 50:
                current_app.config['PASSWORD_MIN_LENGTH'] = value
                new_settings['password_min_length'] = value
        
        if 'require_strong_password' in data:
            value = bool(data['require_strong_password'])
            current_app.config['REQUIRE_STRONG_PASSWORD'] = value
            new_settings['require_strong_password'] = value
        
        # تسجيل التغيير
        if audit_logger and new_settings:
            audit_logger.log_event(
                AuditEventType.SYSTEM_CONFIG_CHANGED,
                severity=AuditSeverity.HIGH.value,
                user_id=session.get('user_id'),
                old_values=old_settings,
                new_values=new_settings,
                additional_data={'config_type': 'security_settings'}
            )
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث إعدادات الأمان بنجاح',
            'updated_settings': new_settings
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في تحديث إعدادات الأمان: {str(e)}'}), 500

