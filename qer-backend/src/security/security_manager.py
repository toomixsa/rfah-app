"""
مدير الأمان المتقدم لنظام رفاه
يتضمن حماية من الهجمات الشائعة وتشفير البيانات الحساسة
"""

import hashlib
import secrets
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, session
import re
import time
from collections import defaultdict
import ipaddress

class SecurityManager:
    def __init__(self, app=None):
        self.app = app
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()
        self.rate_limits = defaultdict(list)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """تهيئة مدير الأمان مع التطبيق"""
        self.app = app
        
        # إعدادات الأمان الافتراضية
        app.config.setdefault('SECRET_KEY', secrets.token_hex(32))
        app.config.setdefault('JWT_SECRET_KEY', secrets.token_hex(32))
        app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))
        app.config.setdefault('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
        app.config.setdefault('MAX_LOGIN_ATTEMPTS', 5)
        app.config.setdefault('LOCKOUT_DURATION', 900)  # 15 دقيقة
        app.config.setdefault('RATE_LIMIT_REQUESTS', 100)
        app.config.setdefault('RATE_LIMIT_WINDOW', 3600)  # ساعة واحدة
        app.config.setdefault('PASSWORD_MIN_LENGTH', 8)
        app.config.setdefault('REQUIRE_STRONG_PASSWORD', True)
        
        # تسجيل middleware للأمان
        app.before_request(self.security_middleware)
    
    def security_middleware(self):
        """Middleware للأمان يتم تنفيذه قبل كل طلب"""
        client_ip = self.get_client_ip()
        
        # فحص IP المحظور
        if self.is_ip_blocked(client_ip):
            return jsonify({
                'error': 'تم حظر عنوان IP الخاص بك مؤقتاً بسبب النشاط المشبوه',
                'blocked_until': self.get_block_expiry(client_ip)
            }), 429
        
        # فحص معدل الطلبات
        if not self.check_rate_limit(client_ip):
            return jsonify({
                'error': 'تم تجاوز الحد المسموح من الطلبات، يرجى المحاولة لاحقاً',
                'retry_after': 3600
            }), 429
        
        # فحص الأمان للرؤوس
        if not self.validate_security_headers():
            return jsonify({'error': 'طلب غير آمن'}), 400
        
        # حماية من CSRF
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            if not self.validate_csrf_token():
                return jsonify({'error': 'رمز CSRF غير صالح'}), 403
    
    def get_client_ip(self):
        """الحصول على عنوان IP الحقيقي للعميل"""
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
                if self.is_valid_ip(ip):
                    return ip
        
        return request.environ.get('REMOTE_ADDR', '127.0.0.1')
    
    def is_valid_ip(self, ip):
        """التحقق من صحة عنوان IP"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def is_ip_blocked(self, ip):
        """فحص ما إذا كان IP محظوراً"""
        if ip in self.blocked_ips:
            return True
        
        # فحص محاولات تسجيل الدخول الفاشلة
        failed_attempts = self.failed_attempts.get(ip, [])
        recent_attempts = [
            attempt for attempt in failed_attempts
            if time.time() - attempt < current_app.config['LOCKOUT_DURATION']
        ]
        
        return len(recent_attempts) >= current_app.config['MAX_LOGIN_ATTEMPTS']
    
    def get_block_expiry(self, ip):
        """الحصول على وقت انتهاء الحظر"""
        failed_attempts = self.failed_attempts.get(ip, [])
        if failed_attempts:
            last_attempt = max(failed_attempts)
            expiry = last_attempt + current_app.config['LOCKOUT_DURATION']
            return datetime.fromtimestamp(expiry).isoformat()
        return None
    
    def record_failed_login(self, ip):
        """تسجيل محاولة تسجيل دخول فاشلة"""
        self.failed_attempts[ip].append(time.time())
        
        # تنظيف المحاولات القديمة
        cutoff = time.time() - current_app.config['LOCKOUT_DURATION']
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip]
            if attempt > cutoff
        ]
    
    def clear_failed_attempts(self, ip):
        """مسح محاولات تسجيل الدخول الفاشلة بعد نجاح تسجيل الدخول"""
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]
    
    def check_rate_limit(self, ip):
        """فحص معدل الطلبات"""
        now = time.time()
        window = current_app.config['RATE_LIMIT_WINDOW']
        max_requests = current_app.config['RATE_LIMIT_REQUESTS']
        
        # تنظيف الطلبات القديمة
        cutoff = now - window
        self.rate_limits[ip] = [
            timestamp for timestamp in self.rate_limits[ip]
            if timestamp > cutoff
        ]
        
        # فحص الحد الأقصى
        if len(self.rate_limits[ip]) >= max_requests:
            return False
        
        # تسجيل الطلب الحالي
        self.rate_limits[ip].append(now)
        return True
    
    def validate_security_headers(self):
        """التحقق من رؤوس الأمان"""
        # فحص User-Agent
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) < 10:
            return False
        
        # فحص Content-Type للطلبات التي تحتوي على بيانات
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('Content-Type', '')
            if request.data and not content_type:
                return False
        
        return True
    
    def generate_csrf_token(self):
        """إنتاج رمز CSRF"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    def validate_csrf_token(self):
        """التحقق من رمز CSRF"""
        # تجاهل CSRF للطلبات من نفس المصدر في التطوير
        if current_app.config.get('TESTING') or current_app.config.get('DEBUG'):
            return True
        
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        return token and token == session.get('csrf_token')
    
    def hash_password(self, password):
        """تشفير كلمة المرور باستخدام bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed):
        """التحقق من كلمة المرور"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def validate_password_strength(self, password):
        """التحقق من قوة كلمة المرور"""
        if len(password) < current_app.config['PASSWORD_MIN_LENGTH']:
            return False, f"كلمة المرور يجب أن تكون {current_app.config['PASSWORD_MIN_LENGTH']} أحرف على الأقل"
        
        if not current_app.config['REQUIRE_STRONG_PASSWORD']:
            return True, "كلمة المرور صالحة"
        
        # فحص وجود أحرف كبيرة وصغيرة وأرقام ورموز
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        missing = []
        if not has_upper:
            missing.append("أحرف كبيرة")
        if not has_lower:
            missing.append("أحرف صغيرة")
        if not has_digit:
            missing.append("أرقام")
        if not has_special:
            missing.append("رموز خاصة")
        
        if missing:
            return False, f"كلمة المرور يجب أن تحتوي على: {', '.join(missing)}"
        
        # فحص الكلمات الشائعة
        common_passwords = [
            'password', '123456', 'qwerty', 'abc123', 'password123',
            'admin', 'user', 'test', '111111', '000000'
        ]
        
        if password.lower() in common_passwords:
            return False, "كلمة المرور ضعيفة جداً، يرجى اختيار كلمة مرور أقوى"
        
        return True, "كلمة المرور قوية"
    
    def generate_jwt_token(self, user_id, token_type='access'):
        """إنتاج JWT token"""
        now = datetime.utcnow()
        
        if token_type == 'access':
            expires = now + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        else:  # refresh
            expires = now + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        
        payload = {
            'user_id': user_id,
            'type': token_type,
            'iat': now,
            'exp': expires,
            'jti': secrets.token_hex(16)  # JWT ID للإلغاء
        }
        
        return jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
    
    def verify_jwt_token(self, token):
        """التحقق من JWT token"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def sanitize_input(self, data):
        """تنظيف المدخلات من المحتوى الضار"""
        if isinstance(data, str):
            # إزالة HTML tags
            data = re.sub(r'<[^>]+>', '', data)
            # إزالة JavaScript
            data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
            # إزالة SQL injection patterns
            sql_patterns = [
                r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
                r'(--|#|/\*|\*/)',
                r'(\bOR\b.*=.*\bOR\b)',
                r'(\bAND\b.*=.*\bAND\b)'
            ]
            for pattern in sql_patterns:
                data = re.sub(pattern, '', data, flags=re.IGNORECASE)
        
        elif isinstance(data, dict):
            return {key: self.sanitize_input(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        
        return data
    
    def log_security_event(self, event_type, details, severity='INFO'):
        """تسجيل أحداث الأمان"""
        timestamp = datetime.utcnow().isoformat()
        client_ip = self.get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'severity': severity,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'details': details,
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url
        }
        
        # في بيئة الإنتاج، يجب حفظ هذا في قاعدة بيانات أو ملف log
        current_app.logger.info(f"Security Event: {log_entry}")
        
        return log_entry
    
    def encrypt_sensitive_data(self, data):
        """تشفير البيانات الحساسة"""
        from cryptography.fernet import Fernet
        
        # في بيئة الإنتاج، يجب حفظ المفتاح بشكل آمن
        key = current_app.config.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            current_app.config['ENCRYPTION_KEY'] = key
        
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data):
        """فك تشفير البيانات الحساسة"""
        from cryptography.fernet import Fernet
        
        key = current_app.config.get('ENCRYPTION_KEY')
        if not key:
            return None
        
        try:
            f = Fernet(key)
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return None

# ديكوريترز للأمان
def require_auth(f):
    """ديكوريتر للتحقق من المصادقة"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'رمز المصادقة مطلوب'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        security_manager = current_app.extensions.get('security_manager')
        if not security_manager:
            return jsonify({'error': 'خطأ في النظام'}), 500
        
        payload = security_manager.verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'رمز المصادقة غير صالح'}), 401
        
        request.current_user_id = payload['user_id']
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission):
    """ديكوريتر للتحقق من الصلاحيات"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # يجب تنفيذ فحص الصلاحيات هنا
            # هذا مثال مبسط
            user_id = getattr(request, 'current_user_id', None)
            if not user_id:
                return jsonify({'error': 'غير مصرح'}), 401
            
            # فحص الصلاحية من قاعدة البيانات
            # ...
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit(max_requests=100, window=3600):
    """ديكوريتر لتحديد معدل الطلبات"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            security_manager = current_app.extensions.get('security_manager')
            if security_manager:
                client_ip = security_manager.get_client_ip()
                if not security_manager.check_rate_limit(client_ip):
                    return jsonify({
                        'error': 'تم تجاوز الحد المسموح من الطلبات'
                    }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

