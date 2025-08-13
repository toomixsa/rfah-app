from src.models.user import db
from datetime import datetime
import string
import random

class ShortenedUrl(db.Model):
    __tablename__ = 'shortened_urls'
    
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.Text, nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    custom_alias = db.Column(db.String(50), nullable=True)
    title = db.Column(db.String(200), nullable=True)  # عنوان الرابط
    description = db.Column(db.Text, nullable=True)  # وصف الرابط
    clicks = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # تاريخ انتهاء الصلاحية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # للحذف الناعم
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # العلاقة مع سجلات النقرات
    click_logs = db.relationship('ClickLog', backref='url', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, original_url, custom_alias=None, user_id=None, title=None, 
                 description=None, expires_at=None):
        self.original_url = original_url
        self.custom_alias = custom_alias
        self.user_id = user_id
        self.title = title
        self.description = description
        self.expires_at = expires_at
        self.short_code = custom_alias if custom_alias else self.generate_short_code()
    
    def generate_short_code(self):
        """توليد كود قصير عشوائي"""
        characters = string.ascii_letters + string.digits
        while True:
            short_code = ''.join(random.choice(characters) for _ in range(6))
            if not ShortenedUrl.query.filter_by(short_code=short_code).first():
                return short_code
    
    def is_expired(self):
        """التحقق من انتهاء صلاحية الرابط"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def soft_delete(self):
        """الحذف الناعم للرابط"""
        self.deleted_at = datetime.utcnow()
        self.is_active = False
    
    def restore(self):
        """استعادة الرابط المحذوف"""
        self.deleted_at = None
        self.is_active = True
    
    def to_dict(self, include_stats=False):
        result = {
            'id': self.id,
            'original_url': self.original_url,
            'short_code': self.short_code,
            'shortened_url': f'https://rfah.me/{self.short_code}',
            'custom_alias': self.custom_alias,
            'title': self.title,
            'description': self.description,
            'clicks': self.clicks,
            'is_active': self.is_active,
            'expires_at': self.expires_at.strftime('%Y-%m-%d %H:%M:%S') if self.expires_at else None,
            'is_expired': self.is_expired(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'deleted_at': self.deleted_at.strftime('%Y-%m-%d %H:%M:%S') if self.deleted_at else None,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'غير محدد',
            'user_username': self.user.username if self.user else 'غير محدد'
        }
        
        if include_stats:
            result['stats'] = self.get_click_stats()
        
        return result
    
    def get_click_stats(self):
        """جلب إحصائيات النقرات المفصلة"""
        from src.models.analytics import ClickLog
        from sqlalchemy import func, extract
        
        # إحصائيات عامة
        total_clicks = len(self.click_logs)
        unique_ips = db.session.query(func.count(func.distinct(ClickLog.ip_address))).filter_by(url_id=self.id).scalar()
        
        # النقرات حسب اليوم (آخر 30 يوم)
        daily_clicks = db.session.query(
            func.date(ClickLog.timestamp).label('date'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == self.id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=30)
        ).group_by(func.date(ClickLog.timestamp)).all()
        
        # النقرات حسب الساعة (آخر 24 ساعة)
        hourly_clicks = db.session.query(
            extract('hour', ClickLog.timestamp).label('hour'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == self.id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(hours=24)
        ).group_by(extract('hour', ClickLog.timestamp)).all()
        
        return {
            'total_clicks': total_clicks,
            'unique_visitors': unique_ips,
            'daily_clicks': [{'date': str(row.date), 'clicks': row.clicks} for row in daily_clicks],
            'hourly_clicks': [{'hour': int(row.hour), 'clicks': row.clicks} for row in hourly_clicks],
            'first_click': self.click_logs[0].timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.click_logs else None,
            'last_click': self.click_logs[-1].timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.click_logs else None
        }
    
    @staticmethod
    def get_by_short_code(short_code):
        return ShortenedUrl.query.filter_by(short_code=short_code, is_active=True, deleted_at=None).first()
    
    @staticmethod
    def get_active_urls():
        """جلب جميع الروابط النشطة (غير المحذوفة)"""
        return ShortenedUrl.query.filter_by(is_active=True, deleted_at=None).all()
    
    @staticmethod
    def get_deleted_urls():
        """جلب جميع الروابط المحذوفة"""
        return ShortenedUrl.query.filter(ShortenedUrl.deleted_at.isnot(None)).all()
    
    @staticmethod
    def get_by_user(user_id, include_deleted=False):
        """جلب الروابط حسب المستخدم"""
        query = ShortenedUrl.query.filter_by(user_id=user_id)
        if not include_deleted:
            query = query.filter_by(is_active=True, deleted_at=None)
        return query.all()
    
    def increment_clicks(self, ip_address=None, user_agent=None, referer=None):
        """زيادة عدد النقرات مع تسجيل تفاصيل النقرة"""
        self.clicks += 1
        
        # تسجيل تفاصيل النقرة
        from src.models.analytics import ClickLog
        click_log = ClickLog(
            url_id=self.id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer
        )
        db.session.add(click_log)
        db.session.commit()

