"""
نقاط النهاية للتحليلات والتقارير المتقدمة
"""

from flask import Blueprint, request, jsonify, session, send_file
from src.analytics import AnalyticsEngine
from src.security import require_auth, require_permission
from src.models.user import User
from datetime import datetime, timedelta
import json
import io
import csv

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard-stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """الحصول على إحصائيات لوحة التحكم"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        # معاملات الاستعلام
        days = int(request.args.get('days', 30))
        days = min(days, 365)  # حد أقصى سنة واحدة
        
        user_id = request.args.get('user_id')
        if user_id:
            user_id = int(user_id)
            # التحقق من الصلاحية لعرض بيانات مستخدم آخر
            if user_id != session.get('user_id'):
                # يجب أن يكون لديه صلاحية عرض بيانات المستخدمين الآخرين
                pass  # سيتم فحص الصلاحية في الديكوريتر
        else:
            user_id = session.get('user_id')
        
        stats = analytics_engine.get_dashboard_stats(user_id, days)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات لوحة التحكم: {str(e)}'}), 500

@analytics_bp.route('/user-performance/<int:user_id>', methods=['GET'])
@require_auth
@require_permission('analytics.view_users')
def get_user_performance(user_id):
    """الحصول على مؤشرات أداء مستخدم محدد"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        days = int(request.args.get('days', 30))
        days = min(days, 365)
        
        performance = analytics_engine.get_user_performance(user_id, days)
        
        if not performance:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        return jsonify({
            'success': True,
            'data': performance
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب مؤشرات الأداء: {str(e)}'}), 500

@analytics_bp.route('/my-performance', methods=['GET'])
@require_auth
def get_my_performance():
    """الحصول على مؤشرات أداء المستخدم الحالي"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        user_id = session.get('user_id')
        days = int(request.args.get('days', 30))
        days = min(days, 365)
        
        performance = analytics_engine.get_user_performance(user_id, days)
        
        return jsonify({
            'success': True,
            'data': performance
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب مؤشرات الأداء: {str(e)}'}), 500

@analytics_bp.route('/url-stats/<int:url_id>', methods=['GET'])
@require_auth
def get_url_stats(url_id):
    """الحصول على إحصائيات مفصلة لرابط محدد"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        days = int(request.args.get('days', 30))
        days = min(days, 365)
        
        # التحقق من ملكية الرابط أو الصلاحية
        from src.models.url import URL
        url = URL.query.get(url_id)
        if not url:
            return jsonify({'error': 'الرابط غير موجود'}), 404
        
        # التحقق من الصلاحية
        current_user_id = session.get('user_id')
        if url.created_by != current_user_id:
            # يجب أن يكون لديه صلاحية عرض جميع الروابط
            pass  # سيتم فحص الصلاحية في الديكوريتر
        
        stats = analytics_engine.get_url_detailed_stats(url_id, days)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب إحصائيات الرابط: {str(e)}'}), 500

@analytics_bp.route('/comparative-analysis', methods=['POST'])
@require_auth
@require_permission('analytics.compare_users')
def get_comparative_analysis():
    """تحليل مقارن بين المستخدمين"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        days = data.get('days', 30)
        days = min(days, 365)
        
        if not user_ids or len(user_ids) < 2:
            return jsonify({'error': 'يجب تحديد مستخدمين على الأقل للمقارنة'}), 400
        
        if len(user_ids) > 10:
            return jsonify({'error': 'لا يمكن مقارنة أكثر من 10 مستخدمين'}), 400
        
        # التحقق من وجود المستخدمين
        existing_users = User.query.filter(
            User.id.in_(user_ids),
            User.deleted_at.is_(None)
        ).count()
        
        if existing_users != len(user_ids):
            return jsonify({'error': 'بعض المستخدمين غير موجودين'}), 400
        
        comparison = analytics_engine.get_comparative_analysis(user_ids, days)
        
        return jsonify({
            'success': True,
            'data': comparison
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في التحليل المقارن: {str(e)}'}), 500

@analytics_bp.route('/trending-analysis', methods=['GET'])
@require_auth
@require_permission('analytics.view_trends')
def get_trending_analysis():
    """تحليل الاتجاهات والروابط الرائجة"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        days = int(request.args.get('days', 7))
        days = min(days, 30)  # حد أقصى شهر للاتجاهات
        
        trends = analytics_engine.get_trending_analysis(days)
        
        return jsonify({
            'success': True,
            'data': trends
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في تحليل الاتجاهات: {str(e)}'}), 500

@analytics_bp.route('/performance-report', methods=['POST'])
@require_auth
def generate_performance_report():
    """إنتاج تقرير أداء شامل"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        data = request.get_json()
        
        # معاملات التقرير
        user_id = data.get('user_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        # التحقق من الصلاحيات
        current_user_id = session.get('user_id')
        if user_id and user_id != current_user_id:
            # يجب أن يكون لديه صلاحية عرض تقارير المستخدمين الآخرين
            pass  # سيتم فحص الصلاحية في الديكوريتر
        elif not user_id:
            user_id = current_user_id
        
        # تحويل التواريخ
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        
        report = analytics_engine.generate_performance_report(user_id, start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': report
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في إنتاج التقرير: {str(e)}'}), 500

@analytics_bp.route('/export-report', methods=['POST'])
@require_auth
def export_performance_report():
    """تصدير تقرير الأداء كملف CSV"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        data = request.get_json()
        
        # إنتاج التقرير
        user_id = data.get('user_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        current_user_id = session.get('user_id')
        if user_id and user_id != current_user_id:
            pass  # فحص الصلاحية
        elif not user_id:
            user_id = current_user_id
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        
        report = analytics_engine.generate_performance_report(user_id, start_date, end_date)
        
        # إنشاء ملف CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # كتابة الرؤوس
        writer.writerow(['التقرير', 'تقرير أداء نظام رفاه'])
        writer.writerow(['فترة التقرير', f"{report['report_period']['start_date']} إلى {report['report_period']['end_date']}"])
        writer.writerow(['تاريخ الإنتاج', report['generated_at']])
        writer.writerow([])
        
        # الإحصائيات العامة
        if report['dashboard_stats']:
            stats = report['dashboard_stats']
            writer.writerow(['الإحصائيات العامة'])
            writer.writerow(['إجمالي الروابط', stats['total_urls']])
            writer.writerow(['الروابط النشطة', stats['active_urls']])
            writer.writerow(['الروابط المنتهية', stats['expired_urls']])
            writer.writerow(['إجمالي النقرات', stats['total_clicks']])
            writer.writerow(['النقرات في الفترة', stats['period_clicks']])
            writer.writerow(['معدل النقر', f"{stats['click_through_rate']}%"])
            writer.writerow([])
        
        # أداء المستخدم
        if report['user_performance']:
            perf = report['user_performance']
            writer.writerow(['أداء المستخدم'])
            writer.writerow(['اسم المستخدم', perf['username']])
            writer.writerow(['الاسم الكامل', perf['full_name']])
            writer.writerow(['نقاط الأداء', perf['performance_score']])
            writer.writerow(['متوسط النقرات لكل رابط', perf['avg_clicks_per_url']])
            writer.writerow([])
        
        # أفضل الروابط
        if report['dashboard_stats'] and report['dashboard_stats']['top_urls']:
            writer.writerow(['أفضل الروابط'])
            writer.writerow(['العنوان', 'الكود المختصر', 'عدد النقرات'])
            for url in report['dashboard_stats']['top_urls']:
                writer.writerow([url['title'], url['short_code'], url['click_count']])
            writer.writerow([])
        
        # التوصيات
        if report['recommendations']:
            writer.writerow(['التوصيات'])
            writer.writerow(['النوع', 'العنوان', 'الوصف', 'الأولوية'])
            for rec in report['recommendations']:
                writer.writerow([rec['type'], rec['title'], rec['description'], rec['priority']])
        
        # تحويل إلى bytes
        output.seek(0)
        csv_data = output.getvalue().encode('utf-8-sig')  # BOM للدعم العربي في Excel
        
        # إنشاء ملف في الذاكرة
        file_buffer = io.BytesIO(csv_data)
        
        # اسم الملف
        user_name = report['user_performance']['username'] if report['user_performance'] else 'عام'
        filename = f"تقرير_الأداء_{user_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            file_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
    
    except Exception as e:
        return jsonify({'error': f'خطأ في تصدير التقرير: {str(e)}'}), 500

@analytics_bp.route('/team-leaderboard', methods=['GET'])
@require_auth
@require_permission('analytics.view_leaderboard')
def get_team_leaderboard():
    """الحصول على لوحة المتصدرين للفريق"""
    try:
        analytics_engine = current_app.extensions.get('analytics_engine')
        if not analytics_engine:
            return jsonify({'error': 'محرك التحليلات غير متاح'}), 500
        
        days = int(request.args.get('days', 30))
        days = min(days, 365)
        
        # الحصول على جميع المستخدمين النشطين
        active_users = User.query.filter(
            User.deleted_at.is_(None),
            User.is_active == True
        ).all()
        
        user_ids = [user.id for user in active_users]
        
        if not user_ids:
            return jsonify({
                'success': True,
                'data': {
                    'leaderboard': [],
                    'total_users': 0,
                    'period_days': days
                }
            })
        
        # الحصول على التحليل المقارن
        comparison = analytics_engine.get_comparative_analysis(user_ids, days)
        
        # إضافة معلومات إضافية للوحة المتصدرين
        leaderboard = []
        for user_data in comparison['users']:
            # تحديد الشارة حسب الترتيب
            badge = None
            if user_data['rank'] == 1:
                badge = {'type': 'gold', 'title': 'المتصدر الأول'}
            elif user_data['rank'] == 2:
                badge = {'type': 'silver', 'title': 'المركز الثاني'}
            elif user_data['rank'] == 3:
                badge = {'type': 'bronze', 'title': 'المركز الثالث'}
            elif user_data['performance_score'] >= 80:
                badge = {'type': 'star', 'title': 'أداء ممتاز'}
            elif user_data['performance_score'] >= 60:
                badge = {'type': 'thumbs-up', 'title': 'أداء جيد'}
            
            leaderboard.append({
                **user_data,
                'badge': badge
            })
        
        return jsonify({
            'success': True,
            'data': {
                'leaderboard': leaderboard,
                'group_stats': comparison['group_stats'],
                'period_days': days
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب لوحة المتصدرين: {str(e)}'}), 500

@analytics_bp.route('/real-time-stats', methods=['GET'])
@require_auth
def get_real_time_stats():
    """الحصول على الإحصائيات في الوقت الفعلي"""
    try:
        from src.models.analytics import ClickLog
        from src.models.url import URL
        from sqlalchemy import func
        
        # النقرات في آخر ساعة
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_clicks = ClickLog.query.join(URL).filter(
            and_(
                ClickLog.clicked_at >= hour_ago,
                URL.deleted_at.is_(None)
            )
        ).count()
        
        # النقرات في آخر 24 ساعة
        day_ago = datetime.utcnow() - timedelta(days=1)
        daily_clicks = ClickLog.query.join(URL).filter(
            and_(
                ClickLog.clicked_at >= day_ago,
                URL.deleted_at.is_(None)
            )
        ).count()
        
        # أحدث النقرات
        latest_clicks = db.session.query(
            ClickLog.clicked_at,
            URL.title,
            URL.short_code,
            ClickLog.country,
            ClickLog.device_type
        ).join(URL).filter(
            URL.deleted_at.is_(None)
        ).order_by(desc(ClickLog.clicked_at)).limit(10).all()
        
        latest_clicks_data = [
            {
                'clicked_at': click.clicked_at.isoformat(),
                'url_title': click.title,
                'short_code': click.short_code,
                'country': click.country or 'غير محدد',
                'device_type': click.device_type or 'غير محدد'
            }
            for click in latest_clicks
        ]
        
        # المستخدمون النشطون حالياً (آخر 15 دقيقة)
        fifteen_min_ago = datetime.utcnow() - timedelta(minutes=15)
        active_users = db.session.query(func.count(func.distinct(URL.created_by))).join(ClickLog).filter(
            and_(
                ClickLog.clicked_at >= fifteen_min_ago,
                URL.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'recent_clicks_1h': recent_clicks,
                'recent_clicks_24h': daily_clicks,
                'active_users_15m': active_users,
                'latest_clicks': latest_clicks_data,
                'last_updated': datetime.utcnow().isoformat()
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'خطأ في جلب الإحصائيات الفورية: {str(e)}'}), 500

