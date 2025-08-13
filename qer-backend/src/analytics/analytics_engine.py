"""
محرك التحليلات والإحصائيات المتقدم لنظام رفاه
يوفر تحليلات شاملة ومؤشرات أداء لكل موظف ورابط
"""

from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, asc
from collections import defaultdict
import json
from src.models.user import User, db
from src.models.url import ShortenedUrl as URL
from src.models.analytics import ClickLog

class AnalyticsEngine:
    """محرك التحليلات الرئيسي"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """تهيئة محرك التحليلات مع التطبيق"""
        self.app = app
        app.extensions['analytics_engine'] = self
    
    def get_dashboard_stats(self, user_id=None, days=30):
        """الحصول على إحصائيات لوحة التحكم"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # بناء الاستعلام الأساسي
        base_query = db.session.query(URL)
        if user_id:
            base_query = base_query.filter(URL.created_by == user_id)
        
        # إجمالي الروابط
        total_urls = base_query.filter(URL.deleted_at.is_(None)).count()
        
        # الروابط النشطة
        active_urls = base_query.filter(
            and_(
                URL.deleted_at.is_(None),
                URL.is_active == True,
                or_(URL.expires_at.is_(None), URL.expires_at > datetime.utcnow())
            )
        ).count()
        
        # الروابط المنتهية الصلاحية
        expired_urls = base_query.filter(
            and_(
                URL.deleted_at.is_(None),
                URL.expires_at.isnot(None),
                URL.expires_at <= datetime.utcnow()
            )
        ).count()
        
        # إجمالي النقرات
        clicks_query = db.session.query(func.sum(URL.click_count))
        if user_id:
            clicks_query = clicks_query.filter(URL.created_by == user_id)
        
        total_clicks = clicks_query.filter(URL.deleted_at.is_(None)).scalar() or 0
        
        # النقرات في الفترة المحددة
        period_clicks_query = db.session.query(func.count(ClickLog.id)).join(URL)
        if user_id:
            period_clicks_query = period_clicks_query.filter(URL.created_by == user_id)
        
        period_clicks = period_clicks_query.filter(
            and_(
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        # الروابط الجديدة في الفترة
        new_urls = base_query.filter(
            and_(
                URL.created_at >= start_date,
                URL.created_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).count()
        
        # معدل النقر (CTR)
        ctr = (period_clicks / total_urls * 100) if total_urls > 0 else 0
        
        # أكثر الروابط نشاطاً
        top_urls_query = base_query.filter(URL.deleted_at.is_(None)).order_by(desc(URL.click_count)).limit(5)
        top_urls = []
        
        for url in top_urls_query:
            top_urls.append({
                'id': url.id,
                'title': url.title,
                'short_code': url.short_code,
                'click_count': url.click_count,
                'created_at': url.created_at.isoformat()
            })
        
        return {
            'total_urls': total_urls,
            'active_urls': active_urls,
            'expired_urls': expired_urls,
            'total_clicks': total_clicks,
            'period_clicks': period_clicks,
            'new_urls': new_urls,
            'click_through_rate': round(ctr, 2),
            'top_urls': top_urls,
            'period_days': days
        }
    
    def get_user_performance(self, user_id, days=30):
        """الحصول على مؤشرات أداء مستخدم محدد"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        user = User.query.get(user_id)
        if not user:
            return None
        
        # إحصائيات الروابط
        user_urls = URL.query.filter(
            and_(URL.created_by == user_id, URL.deleted_at.is_(None))
        )
        
        total_urls = user_urls.count()
        active_urls = user_urls.filter(
            and_(
                URL.is_active == True,
                or_(URL.expires_at.is_(None), URL.expires_at > datetime.utcnow())
            )
        ).count()
        
        # إحصائيات النقرات
        total_clicks = db.session.query(func.sum(URL.click_count)).filter(
            and_(URL.created_by == user_id, URL.deleted_at.is_(None))
        ).scalar() or 0
        
        # النقرات في الفترة المحددة
        period_clicks = db.session.query(func.count(ClickLog.id)).join(URL).filter(
            and_(
                URL.created_by == user_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        # متوسط النقرات لكل رابط
        avg_clicks_per_url = (total_clicks / total_urls) if total_urls > 0 else 0
        
        # النشاط اليومي
        daily_activity = self._get_daily_activity(user_id, start_date, end_date)
        
        # أفضل الروابط
        top_urls = user_urls.order_by(desc(URL.click_count)).limit(10).all()
        top_urls_data = []
        
        for url in top_urls:
            # الحصول على إحصائيات مفصلة للرابط
            url_stats = self.get_url_detailed_stats(url.id, days)
            top_urls_data.append({
                'id': url.id,
                'title': url.title,
                'short_code': url.short_code,
                'click_count': url.click_count,
                'created_at': url.created_at.isoformat(),
                'stats': url_stats
            })
        
        # تقييم الأداء
        performance_score = self._calculate_performance_score(
            total_urls, total_clicks, active_urls, period_clicks, days
        )
        
        return {
            'user_id': user_id,
            'username': user.username,
            'full_name': user.full_name,
            'total_urls': total_urls,
            'active_urls': active_urls,
            'total_clicks': total_clicks,
            'period_clicks': period_clicks,
            'avg_clicks_per_url': round(avg_clicks_per_url, 2),
            'performance_score': performance_score,
            'daily_activity': daily_activity,
            'top_urls': top_urls_data,
            'period_days': days
        }
    
    def get_url_detailed_stats(self, url_id, days=30):
        """الحصول على إحصائيات مفصلة لرابط محدد"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        url = URL.query.get(url_id)
        if not url:
            return None
        
        # النقرات في الفترة المحددة
        period_clicks = ClickLog.query.filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).count()
        
        # النقرات اليومية
        daily_clicks = self._get_daily_clicks(url_id, start_date, end_date)
        
        # الإحصائيات الجغرافية
        geographic_stats = self._get_geographic_stats(url_id, start_date, end_date)
        
        # إحصائيات الأجهزة
        device_stats = self._get_device_stats(url_id, start_date, end_date)
        
        # إحصائيات المتصفحات
        browser_stats = self._get_browser_stats(url_id, start_date, end_date)
        
        # إحصائيات المصادر
        referrer_stats = self._get_referrer_stats(url_id, start_date, end_date)
        
        # أوقات الذروة
        peak_hours = self._get_peak_hours(url_id, start_date, end_date)
        
        # معدل النقر اليومي
        daily_avg = period_clicks / days if days > 0 else 0
        
        return {
            'url_id': url_id,
            'title': url.title,
            'short_code': url.short_code,
            'total_clicks': url.click_count,
            'period_clicks': period_clicks,
            'daily_average': round(daily_avg, 2),
            'daily_clicks': daily_clicks,
            'geographic_stats': geographic_stats,
            'device_stats': device_stats,
            'browser_stats': browser_stats,
            'referrer_stats': referrer_stats,
            'peak_hours': peak_hours,
            'created_at': url.created_at.isoformat(),
            'last_clicked': url.last_clicked_at.isoformat() if url.last_clicked_at else None
        }
    
    def get_comparative_analysis(self, user_ids, days=30):
        """تحليل مقارن بين المستخدمين"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        comparison_data = []
        
        for user_id in user_ids:
            user_performance = self.get_user_performance(user_id, days)
            if user_performance:
                comparison_data.append(user_performance)
        
        # ترتيب حسب النقاط
        comparison_data.sort(key=lambda x: x['performance_score'], reverse=True)
        
        # إضافة الترتيب
        for i, user_data in enumerate(comparison_data):
            user_data['rank'] = i + 1
        
        # إحصائيات المجموعة
        total_urls = sum(user['total_urls'] for user in comparison_data)
        total_clicks = sum(user['total_clicks'] for user in comparison_data)
        avg_performance = sum(user['performance_score'] for user in comparison_data) / len(comparison_data) if comparison_data else 0
        
        return {
            'users': comparison_data,
            'group_stats': {
                'total_users': len(comparison_data),
                'total_urls': total_urls,
                'total_clicks': total_clicks,
                'average_performance': round(avg_performance, 2)
            },
            'period_days': days
        }
    
    def get_trending_analysis(self, days=7):
        """تحليل الاتجاهات والروابط الرائجة"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # الروابط الأكثر نمواً
        growing_urls = db.session.query(
            URL.id,
            URL.title,
            URL.short_code,
            func.count(ClickLog.id).label('recent_clicks')
        ).join(ClickLog).filter(
            and_(
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).group_by(URL.id).order_by(desc('recent_clicks')).limit(10).all()
        
        # المستخدمون الأكثر نشاطاً
        active_users = db.session.query(
            User.id,
            User.username,
            User.full_name,
            func.count(ClickLog.id).label('recent_clicks')
        ).join(URL, URL.created_by == User.id).join(ClickLog).filter(
            and_(
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None),
                User.deleted_at.is_(None)
            )
        ).group_by(User.id).order_by(desc('recent_clicks')).limit(10).all()
        
        # الاتجاهات الزمنية
        hourly_trends = self._get_hourly_trends(start_date, end_date)
        
        return {
            'trending_urls': [
                {
                    'id': url.id,
                    'title': url.title,
                    'short_code': url.short_code,
                    'recent_clicks': url.recent_clicks
                }
                for url in growing_urls
            ],
            'active_users': [
                {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'recent_clicks': user.recent_clicks
                }
                for user in active_users
            ],
            'hourly_trends': hourly_trends,
            'period_days': days
        }
    
    def generate_performance_report(self, user_id=None, start_date=None, end_date=None):
        """إنتاج تقرير أداء شامل"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        days = (end_date - start_date).days
        
        # إحصائيات عامة
        dashboard_stats = self.get_dashboard_stats(user_id, days)
        
        # إحصائيات المستخدم (إذا تم تحديده)
        user_performance = None
        if user_id:
            user_performance = self.get_user_performance(user_id, days)
        
        # تحليل الاتجاهات
        trending_analysis = self.get_trending_analysis(min(days, 7))
        
        # أفضل الأوقات للنشر
        best_times = self._get_best_posting_times(user_id, start_date, end_date)
        
        # توصيات التحسين
        recommendations = self._generate_recommendations(dashboard_stats, user_performance)
        
        return {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'dashboard_stats': dashboard_stats,
            'user_performance': user_performance,
            'trending_analysis': trending_analysis,
            'best_posting_times': best_times,
            'recommendations': recommendations,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _get_daily_activity(self, user_id, start_date, end_date):
        """الحصول على النشاط اليومي للمستخدم"""
        daily_data = db.session.query(
            func.date(ClickLog.clicked_at).label('date'),
            func.count(ClickLog.id).label('clicks')
        ).join(URL).filter(
            and_(
                URL.created_by == user_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).group_by(func.date(ClickLog.clicked_at)).all()
        
        # تحويل إلى قاموس
        activity_dict = {str(row.date): row.clicks for row in daily_data}
        
        # ملء الأيام المفقودة بالصفر
        current_date = start_date.date()
        end_date_only = end_date.date()
        daily_activity = []
        
        while current_date <= end_date_only:
            daily_activity.append({
                'date': str(current_date),
                'clicks': activity_dict.get(str(current_date), 0)
            })
            current_date += timedelta(days=1)
        
        return daily_activity
    
    def _get_daily_clicks(self, url_id, start_date, end_date):
        """الحصول على النقرات اليومية لرابط محدد"""
        daily_data = db.session.query(
            func.date(ClickLog.clicked_at).label('date'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).group_by(func.date(ClickLog.clicked_at)).all()
        
        # تحويل إلى قاموس
        clicks_dict = {str(row.date): row.clicks for row in daily_data}
        
        # ملء الأيام المفقودة بالصفر
        current_date = start_date.date()
        end_date_only = end_date.date()
        daily_clicks = []
        
        while current_date <= end_date_only:
            daily_clicks.append({
                'date': str(current_date),
                'clicks': clicks_dict.get(str(current_date), 0)
            })
            current_date += timedelta(days=1)
        
        return daily_clicks
    
    def _get_geographic_stats(self, url_id, start_date, end_date):
        """الحصول على الإحصائيات الجغرافية"""
        geo_data = db.session.query(
            ClickLog.country,
            ClickLog.city,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).group_by(ClickLog.country, ClickLog.city).order_by(desc('clicks')).limit(20).all()
        
        return [
            {
                'country': row.country or 'غير محدد',
                'city': row.city or 'غير محدد',
                'clicks': row.clicks
            }
            for row in geo_data
        ]
    
    def _get_device_stats(self, url_id, start_date, end_date):
        """الحصول على إحصائيات الأجهزة"""
        device_data = db.session.query(
            ClickLog.device_type,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).group_by(ClickLog.device_type).order_by(desc('clicks')).all()
        
        return [
            {
                'device_type': row.device_type or 'غير محدد',
                'clicks': row.clicks
            }
            for row in device_data
        ]
    
    def _get_browser_stats(self, url_id, start_date, end_date):
        """الحصول على إحصائيات المتصفحات"""
        browser_data = db.session.query(
            ClickLog.browser,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).group_by(ClickLog.browser).order_by(desc('clicks')).all()
        
        return [
            {
                'browser': row.browser or 'غير محدد',
                'clicks': row.clicks
            }
            for row in browser_data
        ]
    
    def _get_referrer_stats(self, url_id, start_date, end_date):
        """الحصول على إحصائيات المصادر"""
        referrer_data = db.session.query(
            ClickLog.referrer,
            func.count(ClickLog.id).label('clicks')
        ).filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).group_by(ClickLog.referrer).order_by(desc('clicks')).limit(10).all()
        
        return [
            {
                'referrer': row.referrer or 'مباشر',
                'clicks': row.clicks
            }
            for row in referrer_data
        ]
    
    def _get_peak_hours(self, url_id, start_date, end_date):
        """الحصول على أوقات الذروة"""
        hourly_data = db.session.query(
            func.extract('hour', ClickLog.clicked_at).label('hour'),
            func.count(ClickLog.id).label('clicks')
        ).filter(
            and_(
                ClickLog.url_id == url_id,
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date
            )
        ).group_by(func.extract('hour', ClickLog.clicked_at)).order_by('hour').all()
        
        return [
            {
                'hour': int(row.hour),
                'clicks': row.clicks
            }
            for row in hourly_data
        ]
    
    def _get_hourly_trends(self, start_date, end_date):
        """الحصول على الاتجاهات الساعية"""
        hourly_data = db.session.query(
            func.extract('hour', ClickLog.clicked_at).label('hour'),
            func.count(ClickLog.id).label('clicks')
        ).join(URL).filter(
            and_(
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).group_by(func.extract('hour', ClickLog.clicked_at)).order_by('hour').all()
        
        return [
            {
                'hour': int(row.hour),
                'clicks': row.clicks
            }
            for row in hourly_data
        ]
    
    def _get_best_posting_times(self, user_id, start_date, end_date):
        """الحصول على أفضل أوقات النشر"""
        query = db.session.query(
            func.extract('hour', ClickLog.clicked_at).label('hour'),
            func.extract('dow', ClickLog.clicked_at).label('day_of_week'),
            func.count(ClickLog.id).label('clicks')
        ).join(URL)
        
        if user_id:
            query = query.filter(URL.created_by == user_id)
        
        time_data = query.filter(
            and_(
                ClickLog.clicked_at >= start_date,
                ClickLog.clicked_at <= end_date,
                URL.deleted_at.is_(None)
            )
        ).group_by(
            func.extract('hour', ClickLog.clicked_at),
            func.extract('dow', ClickLog.clicked_at)
        ).order_by(desc('clicks')).limit(10).all()
        
        days_map = {
            0: 'الأحد', 1: 'الاثنين', 2: 'الثلاثاء', 3: 'الأربعاء',
            4: 'الخميس', 5: 'الجمعة', 6: 'السبت'
        }
        
        return [
            {
                'hour': int(row.hour),
                'day_of_week': days_map.get(int(row.day_of_week), 'غير محدد'),
                'clicks': row.clicks
            }
            for row in time_data
        ]
    
    def _calculate_performance_score(self, total_urls, total_clicks, active_urls, period_clicks, days):
        """حساب نقاط الأداء"""
        score = 0
        
        # نقاط الإنتاجية (عدد الروابط)
        if total_urls > 0:
            score += min(total_urls * 2, 20)  # حد أقصى 20 نقطة
        
        # نقاط الفعالية (النقرات)
        if total_clicks > 0:
            score += min(total_clicks / 10, 30)  # حد أقصى 30 نقطة
        
        # نقاط النشاط (الروابط النشطة)
        if total_urls > 0:
            activity_ratio = active_urls / total_urls
            score += activity_ratio * 20  # حد أقصى 20 نقطة
        
        # نقاط الاستمرارية (النشاط الحديث)
        if days > 0:
            daily_avg = period_clicks / days
            score += min(daily_avg * 2, 30)  # حد أقصى 30 نقطة
        
        return min(round(score, 2), 100)  # حد أقصى 100 نقطة
    
    def _generate_recommendations(self, dashboard_stats, user_performance):
        """إنتاج توصيات التحسين"""
        recommendations = []
        
        if dashboard_stats:
            # توصيات عامة
            if dashboard_stats['click_through_rate'] < 5:
                recommendations.append({
                    'type': 'improvement',
                    'title': 'تحسين معدل النقر',
                    'description': 'معدل النقر منخفض، يُنصح بتحسين عناوين الروابط وأوصافها',
                    'priority': 'high'
                })
            
            if dashboard_stats['expired_urls'] > dashboard_stats['active_urls']:
                recommendations.append({
                    'type': 'maintenance',
                    'title': 'تجديد الروابط المنتهية',
                    'description': 'لديك روابط منتهية الصلاحية أكثر من النشطة، يُنصح بتجديدها',
                    'priority': 'medium'
                })
        
        if user_performance:
            # توصيات للمستخدم
            if user_performance['performance_score'] < 50:
                recommendations.append({
                    'type': 'training',
                    'title': 'تحسين الأداء',
                    'description': 'نقاط الأداء منخفضة، يُنصح بزيادة النشاط وتحسين جودة الروابط',
                    'priority': 'high'
                })
            
            if user_performance['avg_clicks_per_url'] < 10:
                recommendations.append({
                    'type': 'strategy',
                    'title': 'تحسين استراتيجية المشاركة',
                    'description': 'متوسط النقرات منخفض، يُنصح بمشاركة الروابط في أوقات أفضل',
                    'priority': 'medium'
                })
        
        return recommendations

