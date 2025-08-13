from src.models.user import db
from datetime import datetime
from sqlalchemy import func, extract
from user_agents import parse

class ClickLog(db.Model):
    __tablename__ = 'click_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('shortened_urls.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # دعم IPv6
    user_agent = db.Column(db.Text, nullable=True)
    referer = db.Column(db.Text, nullable=True)  # الموقع المرجعي
    country = db.Column(db.String(100), nullable=True)  # البلد
    city = db.Column(db.String(100), nullable=True)  # المدينة
    device_type = db.Column(db.String(50), nullable=True)  # نوع الجهاز
    browser = db.Column(db.String(100), nullable=True)  # المتصفح
    os = db.Column(db.String(100), nullable=True)  # نظام التشغيل
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, url_id, ip_address=None, user_agent=None, referer=None):
        self.url_id = url_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.referer = referer
        
        # تحليل معلومات المتصفح والجهاز
        if user_agent:
            self.parse_user_agent(user_agent)
    
    def parse_user_agent(self, user_agent_string):
        """تحليل معلومات المتصفح والجهاز من User Agent"""
        try:
            user_agent = parse(user_agent_string)
            self.browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
            self.os = f"{user_agent.os.family} {user_agent.os.version_string}"
            
            if user_agent.is_mobile:
                self.device_type = 'mobile'
            elif user_agent.is_tablet:
                self.device_type = 'tablet'
            elif user_agent.is_pc:
                self.device_type = 'desktop'
            else:
                self.device_type = 'other'
        except:
            # في حالة فشل التحليل، استخدم قيم افتراضية
            self.browser = 'Unknown'
            self.os = 'Unknown'
            self.device_type = 'unknown'
    
    def to_dict(self):
        return {
            'id': self.id,
            'url_id': self.url_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'referer': self.referer,
            'country': self.country,
            'city': self.city,
            'device_type': self.device_type,
            'browser': self.browser,
            'os': self.os,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }


class Analytics:
    """فئة لتوليد التقارير والإحصائيات المتقدمة"""
    
    @staticmethod
    def get_user_stats(user_id, days=30):
        """جلب إحصائيات مستخدم محدد"""
        from src.models.url import ShortenedUrl
        
        # الروابط الخاصة بالمستخدم
        user_urls = ShortenedUrl.query.filter_by(user_id=user_id, is_active=True, deleted_at=None).all()
        
        # إجمالي الروابط والنقرات
        total_urls = len(user_urls)
        total_clicks = sum(url.clicks for url in user_urls)
        
        # النقرات خلال فترة محددة
        recent_clicks = db.session.query(func.sum(ShortenedUrl.clicks)).join(ClickLog).filter(
            ShortenedUrl.user_id == user_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).scalar() or 0
        
        # أكثر الروابط نقراً
        top_urls = sorted(user_urls, key=lambda x: x.clicks, reverse=True)[:5]
        
        # النقرات حسب اليوم
        daily_clicks = db.session.query(
            func.date(ClickLog.timestamp).label('date'),
            func.count(ClickLog.id).label('clicks')
        ).join(ShortenedUrl).filter(
            ShortenedUrl.user_id == user_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(func.date(ClickLog.timestamp)).all()
        
        return {
            'user_id': user_id,
            'total_urls': total_urls,
            'total_clicks': total_clicks,
            'recent_clicks': recent_clicks,
            'average_clicks_per_url': round(total_clicks / total_urls, 2) if total_urls > 0 else 0,
            'top_urls': [url.to_dict() for url in top_urls],
            'daily_clicks': [{'date': str(row.date), 'clicks': row.clicks} for row in daily_clicks]
        }
    
    @staticmethod
    def get_system_stats(days=30):
        """جلب إحصائيات النظام العامة"""
        from src.models.url import ShortenedUrl
        from src.models.user import User
        
        # إحصائيات عامة
        total_users = User.query.filter_by(is_active=True, deleted_at=None).count()
        total_urls = ShortenedUrl.query.filter_by(is_active=True, deleted_at=None).count()
        total_clicks = db.session.query(func.sum(ShortenedUrl.clicks)).filter_by(is_active=True, deleted_at=None).scalar() or 0
        
        # إحصائيات الفترة الأخيرة
        recent_users = User.query.filter(
            User.created_at >= datetime.utcnow() - datetime.timedelta(days=days),
            User.is_active == True,
            User.deleted_at.is_(None)
        ).count()
        
        recent_urls = ShortenedUrl.query.filter(
            ShortenedUrl.created_at >= datetime.utcnow() - datetime.timedelta(days=days),
            ShortenedUrl.is_active == True,
            ShortenedUrl.deleted_at.is_(None)
        ).count()
        
        recent_clicks = ClickLog.query.filter(
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).count()
        
        # أكثر المستخدمين نشاطاً
        top_users = db.session.query(
            User.id, User.full_name, User.username,
            func.count(ShortenedUrl.id).label('urls_count'),
            func.sum(ShortenedUrl.clicks).label('total_clicks')
        ).join(ShortenedUrl).filter(
            User.is_active == True,
            User.deleted_at.is_(None),
            ShortenedUrl.is_active == True,
            ShortenedUrl.deleted_at.is_(None)
        ).group_by(User.id).order_by(func.sum(ShortenedUrl.clicks).desc()).limit(10).all()
        
        # أكثر الروابط نقراً
        top_urls = ShortenedUrl.query.filter_by(is_active=True, deleted_at=None).order_by(ShortenedUrl.clicks.desc()).limit(10).all()
        
        # النقرات حسب اليوم
        daily_clicks = db.session.query(
            func.date(ClickLog.timestamp).label('date'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(func.date(ClickLog.timestamp)).all()
        
        # النقرات حسب نوع الجهاز
        device_stats = db.session.query(
            ClickLog.device_type,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(ClickLog.device_type).all()
        
        # النقرات حسب المتصفح
        browser_stats = db.session.query(
            ClickLog.browser,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(ClickLog.browser).order_by(func.count(ClickLog.id).desc()).limit(10).all()
        
        return {
            'total_users': total_users,
            'total_urls': total_urls,
            'total_clicks': total_clicks,
            'recent_users': recent_users,
            'recent_urls': recent_urls,
            'recent_clicks': recent_clicks,
            'average_clicks_per_url': round(total_clicks / total_urls, 2) if total_urls > 0 else 0,
            'top_users': [
                {
                    'id': row.id,
                    'full_name': row.full_name,
                    'username': row.username,
                    'urls_count': row.urls_count,
                    'total_clicks': row.total_clicks or 0
                } for row in top_users
            ],
            'top_urls': [url.to_dict() for url in top_urls],
            'daily_clicks': [{'date': str(row.date), 'clicks': row.clicks} for row in daily_clicks],
            'device_stats': [{'device_type': row.device_type or 'unknown', 'clicks': row.clicks} for row in device_stats],
            'browser_stats': [{'browser': row.browser or 'unknown', 'clicks': row.clicks} for row in browser_stats]
        }
    
    @staticmethod
    def get_url_detailed_stats(url_id, days=30):
        """جلب إحصائيات مفصلة لرابط محدد"""
        from src.models.url import ShortenedUrl
        
        url = ShortenedUrl.query.get(url_id)
        if not url:
            return None
        
        # النقرات حسب اليوم
        daily_clicks = db.session.query(
            func.date(ClickLog.timestamp).label('date'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == url_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(func.date(ClickLog.timestamp)).all()
        
        # النقرات حسب الساعة (آخر 24 ساعة)
        hourly_clicks = db.session.query(
            extract('hour', ClickLog.timestamp).label('hour'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == url_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(hours=24)
        ).group_by(extract('hour', ClickLog.timestamp)).all()
        
        # النقرات حسب نوع الجهاز
        device_clicks = db.session.query(
            ClickLog.device_type,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == url_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(ClickLog.device_type).all()
        
        # النقرات حسب المتصفح
        browser_clicks = db.session.query(
            ClickLog.browser,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == url_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(ClickLog.browser).all()
        
        # المواقع المرجعية
        referer_clicks = db.session.query(
            ClickLog.referer,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            ClickLog.url_id == url_id,
            ClickLog.referer.isnot(None),
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).group_by(ClickLog.referer).order_by(func.count(ClickLog.id).desc()).limit(10).all()
        
        # الزوار الفريدون
        unique_visitors = db.session.query(func.count(func.distinct(ClickLog.ip_address))).filter(
            ClickLog.url_id == url_id,
            ClickLog.timestamp >= datetime.utcnow() - datetime.timedelta(days=days)
        ).scalar()
        
        return {
            'url': url.to_dict(),
            'unique_visitors': unique_visitors,
            'daily_clicks': [{'date': str(row.date), 'clicks': row.clicks} for row in daily_clicks],
            'hourly_clicks': [{'hour': int(row.hour), 'clicks': row.clicks} for row in hourly_clicks],
            'device_clicks': [{'device_type': row.device_type or 'unknown', 'clicks': row.clicks} for row in device_clicks],
            'browser_clicks': [{'browser': row.browser or 'unknown', 'clicks': row.clicks} for row in browser_clicks],
            'referer_clicks': [{'referer': row.referer, 'clicks': row.clicks} for row in referer_clicks]
        }

