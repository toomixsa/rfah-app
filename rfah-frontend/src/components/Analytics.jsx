import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  MousePointer,
  Calendar,
  Download,
  Filter,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const Analytics = ({ user }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30');
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    loadAnalytics();
  }, [dateRange]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/urls/my-stats?days=${dateRange}`);
      const data = await response.json();
      
      if (data.success) {
        setStats(data.stats);
        setChartData(data.stats.daily_clicks || []);
      }
    } catch (error) {
      console.error('خطأ في جلب الإحصائيات:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, title, value, subtitle, trend, color = 'primary' }) => (
    <div className={`analytics-card ${color}`}>
      <div className="card-header">
        <div className="card-icon">
          <Icon size={24} />
        </div>
        {trend && (
          <div className={`trend ${trend > 0 ? 'positive' : 'negative'}`}>
            <TrendingUp size={16} />
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      <div className="card-content">
        <h3>{title}</h3>
        <div className="card-value">{value}</div>
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
    </div>
  );

  const SimpleChart = ({ data, title }) => {
    if (!data || data.length === 0) {
      return (
        <div className="chart-placeholder">
          <BarChart3 size={48} />
          <p>لا توجد بيانات للعرض</p>
        </div>
      );
    }

    const maxValue = Math.max(...data.map(item => item.clicks));

    return (
      <div className="simple-chart">
        <h3>{title}</h3>
        <div className="chart-bars">
          {data.map((item, index) => (
            <div key={index} className="chart-bar-container">
              <div 
                className="chart-bar"
                style={{ 
                  height: `${maxValue > 0 ? (item.clicks / maxValue) * 100 : 0}%` 
                }}
                title={`${item.date}: ${item.clicks} نقرة`}
              />
              <span className="chart-label">
                {new Date(item.date).getDate()}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>جاري تحميل الإحصائيات...</p>
      </div>
    );
  }

  return (
    <div className="analytics">
      {/* رأس الصفحة */}
      <div className="page-header">
        <div className="header-content">
          <h1>التقارير والإحصائيات</h1>
          <p>تتبع أداء الروابط المختصرة وتحليل البيانات</p>
        </div>
        <div className="header-actions">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="date-range-select"
          >
            <option value="7">آخر 7 أيام</option>
            <option value="30">آخر 30 يوم</option>
            <option value="90">آخر 3 أشهر</option>
            <option value="365">آخر سنة</option>
          </select>
          <Button variant="outline" onClick={loadAnalytics}>
            <RefreshCw size={16} />
            تحديث
          </Button>
          <Button>
            <Download size={16} />
            تصدير التقرير
          </Button>
        </div>
      </div>

      {/* الإحصائيات الرئيسية */}
      <div className="analytics-grid">
        <StatCard
          icon={BarChart3}
          title="إجمالي الروابط"
          value={stats?.total_urls || 0}
          subtitle="الروابط المنشأة"
          color="primary"
        />
        <StatCard
          icon={MousePointer}
          title="إجمالي النقرات"
          value={stats?.total_clicks || 0}
          subtitle="النقرات الكلية"
          color="success"
        />
        <StatCard
          icon={TrendingUp}
          title="النقرات الحديثة"
          value={stats?.recent_clicks || 0}
          subtitle={`آخر ${dateRange} يوم`}
          color="info"
        />
        <StatCard
          icon={BarChart3}
          title="متوسط النقرات"
          value={stats?.average_clicks_per_url || 0}
          subtitle="لكل رابط"
          color="warning"
        />
      </div>

      {/* الرسوم البيانية */}
      <div className="charts-section">
        <div className="chart-container">
          <SimpleChart 
            data={chartData} 
            title={`النقرات اليومية - آخر ${dateRange} يوم`}
          />
        </div>
      </div>

      {/* أكثر الروابط نشاطاً */}
      <div className="top-urls-section">
        <h2>أكثر الروابط نشاطاً</h2>
        {stats?.top_urls && stats.top_urls.length > 0 ? (
          <div className="top-urls-list">
            {stats.top_urls.map((url, index) => (
              <div key={url.id} className="top-url-item">
                <div className="url-rank">#{index + 1}</div>
                <div className="url-info">
                  <h4>{url.title || 'بدون عنوان'}</h4>
                  <p className="url-link">rfah.me/{url.short_code}</p>
                </div>
                <div className="url-stats">
                  <div className="stat">
                    <span className="stat-value">{url.clicks}</span>
                    <span className="stat-label">نقرة</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <BarChart3 size={48} />
            <h3>لا توجد بيانات</h3>
            <p>لا توجد روابط لعرض إحصائياتها</p>
          </div>
        )}
      </div>

      {/* ملخص الأداء */}
      <div className="performance-summary">
        <h2>ملخص الأداء</h2>
        <div className="summary-grid">
          <div className="summary-card">
            <h3>معدل النقر</h3>
            <div className="summary-value">
              {stats?.total_urls > 0 
                ? `${((stats.total_clicks / stats.total_urls) * 100).toFixed(1)}%`
                : '0%'
              }
            </div>
            <p>متوسط النقرات لكل رابط</p>
          </div>
          
          <div className="summary-card">
            <h3>النمو الشهري</h3>
            <div className="summary-value">+12%</div>
            <p>مقارنة بالشهر الماضي</p>
          </div>
          
          <div className="summary-card">
            <h3>أفضل يوم</h3>
            <div className="summary-value">
              {chartData.length > 0 
                ? new Date(chartData.reduce((max, item) => 
                    item.clicks > max.clicks ? item : max
                  ).date).toLocaleDateString('ar-SA')
                : 'غير متاح'
              }
            </div>
            <p>اليوم الأكثر نشاطاً</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;

