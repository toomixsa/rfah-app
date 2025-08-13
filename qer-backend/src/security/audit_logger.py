"""
نظام تسجيل المراجعة والأنشطة لنظام رفاه
يسجل جميع العمليات المهمة لأغراض المراجعة والأمان
"""

import json
from datetime import datetime
from enum import Enum
from flask import request, session, current_app
from src.models.user import db

class AuditEventType(Enum):
    """أنواع أحداث المراجعة"""
    # أحداث المصادقة
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    
    # أحداث المستخدمين
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_RESTORED = "user_restored"
    USER_ROLE_CHANGED = "user_role_changed"
    
    # أحداث الروابط
    URL_CREATED = "url_created"
    URL_UPDATED = "url_updated"
    URL_DELETED = "url_deleted"
    URL_RESTORED = "url_restored"
    URL_ACCESSED = "url_accessed"
    
    # أحداث الأدوار والصلاحيات
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    ROLE_RESTORED = "role_restored"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    
    # أحداث الأمان
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    IP_BLOCKED = "ip_blocked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # أحداث النظام
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    BACKUP_CREATED = "backup_created"

class AuditSeverity(Enum):
    """مستويات خطورة أحداث المراجعة"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditLog(db.Model):
    """نموذج سجل المراجعة"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), default=AuditSeverity.LOW.value, index=True)
    
    # معلومات المستخدم
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(100), nullable=True)
    
    # معلومات الطلب
    ip_address = db.Column(db.String(45), nullable=True, index=True)  # IPv6 support
    user_agent = db.Column(db.Text, nullable=True)
    endpoint = db.Column(db.String(200), nullable=True)
    method = db.Column(db.String(10), nullable=True)
    
    # تفاصيل الحدث
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(100), nullable=True, index=True)
    old_values = db.Column(db.Text, nullable=True)  # JSON
    new_values = db.Column(db.Text, nullable=True)  # JSON
    additional_data = db.Column(db.Text, nullable=True)  # JSON
    
    # معلومات إضافية
    success = db.Column(db.Boolean, default=True, index=True)
    error_message = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.event_type} by {self.username}>'
    
    def to_dict(self):
        """تحويل السجل إلى قاموس"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'event_type': self.event_type,
            'severity': self.severity,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'endpoint': self.endpoint,
            'method': self.method,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'old_values': json.loads(self.old_values) if self.old_values else None,
            'new_values': json.loads(self.new_values) if self.new_values else None,
            'additional_data': json.loads(self.additional_data) if self.additional_data else None,
            'success': self.success,
            'error_message': self.error_message,
            'session_id': self.session_id
        }

class AuditLogger:
    """مسجل أحداث المراجعة"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """تهيئة مسجل المراجعة مع التطبيق"""
        self.app = app
        app.extensions['audit_logger'] = self
    
    def log_event(self, event_type, **kwargs):
        """تسجيل حدث مراجعة"""
        try:
            # الحصول على معلومات الطلب الحالي
            ip_address = self._get_client_ip()
            user_agent = request.headers.get('User-Agent') if request else None
            endpoint = request.endpoint if request else None
            method = request.method if request else None
            session_id = session.get('session_id') if session else None
            
            # الحصول على معلومات المستخدم
            user_id = kwargs.get('user_id') or session.get('user_id') if session else None
            username = kwargs.get('username')
            
            # إنشاء سجل المراجعة
            audit_log = AuditLog(
                event_type=event_type.value if isinstance(event_type, AuditEventType) else event_type,
                severity=kwargs.get('severity', AuditSeverity.LOW.value),
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                method=method,
                resource_type=kwargs.get('resource_type'),
                resource_id=str(kwargs.get('resource_id')) if kwargs.get('resource_id') else None,
                old_values=json.dumps(kwargs.get('old_values'), ensure_ascii=False) if kwargs.get('old_values') else None,
                new_values=json.dumps(kwargs.get('new_values'), ensure_ascii=False) if kwargs.get('new_values') else None,
                additional_data=json.dumps(kwargs.get('additional_data'), ensure_ascii=False) if kwargs.get('additional_data') else None,
                success=kwargs.get('success', True),
                error_message=kwargs.get('error_message'),
                session_id=session_id
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
            # تسجيل في ملف النظام أيضاً للأحداث المهمة
            if kwargs.get('severity') in [AuditSeverity.HIGH.value, AuditSeverity.CRITICAL.value]:
                current_app.logger.warning(f"High severity audit event: {audit_log.to_dict()}")
            
            return audit_log
            
        except Exception as e:
            # في حالة فشل تسجيل المراجعة، نسجل الخطأ ولا نوقف العملية
            current_app.logger.error(f"Failed to log audit event: {str(e)}")
            return None
    
    def _get_client_ip(self):
        """الحصول على عنوان IP الحقيقي للعميل"""
        if not request:
            return None
            
        # فحص الرؤوس المختلفة للحصول على IP الحقيقي
        headers_to_check = [
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'HTTP_X_FORWARDED_FOR',   # Load balancers
            'HTTP_X_REAL_IP',         # Nginx
            'HTTP_X_FORWARDED',
            'HTTP_X_CLUSTER_CLIENT_IP',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED'
        ]
        
        for header in headers_to_check:
            ip = request.environ.get(header)
            if ip:
                # أخذ أول IP في حالة وجود قائمة
                ip = ip.split(',')[0].strip()
                return ip
        
        return request.environ.get('REMOTE_ADDR')
    
    def log_login_success(self, user_id, username):
        """تسجيل نجاح تسجيل الدخول"""
        return self.log_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            username=username,
            severity=AuditSeverity.LOW.value,
            additional_data={'login_time': datetime.utcnow().isoformat()}
        )
    
    def log_login_failed(self, username, reason):
        """تسجيل فشل تسجيل الدخول"""
        return self.log_event(
            AuditEventType.LOGIN_FAILED,
            username=username,
            severity=AuditSeverity.MEDIUM.value,
            success=False,
            error_message=reason,
            additional_data={'failure_reason': reason}
        )
    
    def log_logout(self, user_id, username):
        """تسجيل تسجيل الخروج"""
        return self.log_event(
            AuditEventType.LOGOUT,
            user_id=user_id,
            username=username,
            severity=AuditSeverity.LOW.value
        )
    
    def log_password_change(self, user_id, username):
        """تسجيل تغيير كلمة المرور"""
        return self.log_event(
            AuditEventType.PASSWORD_CHANGED,
            user_id=user_id,
            username=username,
            severity=AuditSeverity.MEDIUM.value,
            resource_type='user',
            resource_id=user_id
        )
    
    def log_user_created(self, creator_id, creator_username, new_user_data):
        """تسجيل إنشاء مستخدم جديد"""
        return self.log_event(
            AuditEventType.USER_CREATED,
            user_id=creator_id,
            username=creator_username,
            severity=AuditSeverity.MEDIUM.value,
            resource_type='user',
            resource_id=new_user_data.get('id'),
            new_values=new_user_data
        )
    
    def log_user_updated(self, updater_id, updater_username, user_id, old_data, new_data):
        """تسجيل تحديث بيانات المستخدم"""
        return self.log_event(
            AuditEventType.USER_UPDATED,
            user_id=updater_id,
            username=updater_username,
            severity=AuditSeverity.MEDIUM.value,
            resource_type='user',
            resource_id=user_id,
            old_values=old_data,
            new_values=new_data
        )
    
    def log_user_deleted(self, deleter_id, deleter_username, deleted_user_data):
        """تسجيل حذف مستخدم"""
        return self.log_event(
            AuditEventType.USER_DELETED,
            user_id=deleter_id,
            username=deleter_username,
            severity=AuditSeverity.HIGH.value,
            resource_type='user',
            resource_id=deleted_user_data.get('id'),
            old_values=deleted_user_data
        )
    
    def log_url_created(self, creator_id, creator_username, url_data):
        """تسجيل إنشاء رابط جديد"""
        return self.log_event(
            AuditEventType.URL_CREATED,
            user_id=creator_id,
            username=creator_username,
            severity=AuditSeverity.LOW.value,
            resource_type='url',
            resource_id=url_data.get('id'),
            new_values=url_data
        )
    
    def log_url_accessed(self, url_id, url_data, access_info):
        """تسجيل الوصول إلى رابط"""
        return self.log_event(
            AuditEventType.URL_ACCESSED,
            severity=AuditSeverity.LOW.value,
            resource_type='url',
            resource_id=url_id,
            additional_data={
                'url_data': url_data,
                'access_info': access_info
            }
        )
    
    def log_security_violation(self, violation_type, details):
        """تسجيل انتهاك أمني"""
        return self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.HIGH.value,
            success=False,
            error_message=violation_type,
            additional_data=details
        )
    
    def log_suspicious_activity(self, activity_type, details):
        """تسجيل نشاط مشبوه"""
        return self.log_event(
            AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.MEDIUM.value,
            additional_data={
                'activity_type': activity_type,
                'details': details
            }
        )
    
    def get_audit_logs(self, filters=None, page=1, per_page=50):
        """الحصول على سجلات المراجعة مع التصفية"""
        query = AuditLog.query
        
        if filters:
            if filters.get('event_type'):
                query = query.filter(AuditLog.event_type == filters['event_type'])
            
            if filters.get('user_id'):
                query = query.filter(AuditLog.user_id == filters['user_id'])
            
            if filters.get('severity'):
                query = query.filter(AuditLog.severity == filters['severity'])
            
            if filters.get('start_date'):
                query = query.filter(AuditLog.timestamp >= filters['start_date'])
            
            if filters.get('end_date'):
                query = query.filter(AuditLog.timestamp <= filters['end_date'])
            
            if filters.get('ip_address'):
                query = query.filter(AuditLog.ip_address == filters['ip_address'])
            
            if filters.get('resource_type'):
                query = query.filter(AuditLog.resource_type == filters['resource_type'])
            
            if filters.get('success') is not None:
                query = query.filter(AuditLog.success == filters['success'])
        
        # ترتيب حسب التاريخ (الأحدث أولاً)
        query = query.order_by(AuditLog.timestamp.desc())
        
        # تطبيق التصفح
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return {
            'logs': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def get_audit_statistics(self, days=30):
        """الحصول على إحصائيات المراجعة"""
        from datetime import timedelta
        from sqlalchemy import func
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # إحصائيات عامة
        total_events = AuditLog.query.filter(AuditLog.timestamp >= start_date).count()
        
        # إحصائيات حسب نوع الحدث
        event_stats = db.session.query(
            AuditLog.event_type,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date
        ).group_by(AuditLog.event_type).all()
        
        # إحصائيات حسب مستوى الخطورة
        severity_stats = db.session.query(
            AuditLog.severity,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date
        ).group_by(AuditLog.severity).all()
        
        # أكثر المستخدمين نشاطاً
        user_stats = db.session.query(
            AuditLog.username,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.username.isnot(None)
        ).group_by(AuditLog.username).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()
        
        # أكثر عناوين IP نشاطاً
        ip_stats = db.session.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.ip_address.isnot(None)
        ).group_by(AuditLog.ip_address).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()
        
        return {
            'total_events': total_events,
            'period_days': days,
            'event_types': [{'type': stat[0], 'count': stat[1]} for stat in event_stats],
            'severity_levels': [{'severity': stat[0], 'count': stat[1]} for stat in severity_stats],
            'top_users': [{'username': stat[0], 'count': stat[1]} for stat in user_stats],
            'top_ips': [{'ip_address': stat[0], 'count': stat[1]} for stat in ip_stats]
        }
    
    def cleanup_old_logs(self, days_to_keep=365):
        """تنظيف السجلات القديمة"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = AuditLog.query.filter(
            AuditLog.timestamp < cutoff_date
        ).delete()
        
        db.session.commit()
        
        current_app.logger.info(f"Cleaned up {deleted_count} old audit logs")
        
        return deleted_count

