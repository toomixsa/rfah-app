import React, { useState, useEffect } from 'react';
import { 
  Link, 
  MousePointer, 
  Users, 
  TrendingUp,
  Plus,
  BarChart3,
  Clock,
  Globe
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const Dashboard = ({ user }) => {
  const [stats, setStats] = useState({
    totalUrls: 0,
    totalClicks: 0,
    totalUsers: 0,
    recentClicks: 0
  });
  const [recentUrls, setRecentUrls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      // جلب الإحصائيات
      const statsResponse = await fetch('/api/urls/my-stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        if (statsData.success) {
          setStats({
            totalUrls: statsData.stats.total_urls,
            totalClicks: statsData.stats.total_clicks,
            totalUsers: 1, // سيتم تحديثه لاحقاً
            recentClicks: statsData.stats.recent_clicks
          });
        }
      }

      // جلب الروابط الحديثة
      const urlsResponse = await fetch('/api/urls/my-urls');
      if (urlsResponse.ok) {
        const urlsData = await urlsResponse.json();
        if (urlsData.success) {
          setRecentUrls(urlsData.urls.slice(0, 5)); // أحدث 5 روابط
        }
      }
    } catch (error) {
      console.error('خطأ في جلب بيانات لوحة التحكم:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, title, value, subtitle, color = 'primary' }) => (
    <div className={`stat-card ${color}`}>
      <div className="stat-icon">
        <Icon size={24} />
      </div>
      <div className="stat-content">
        <h3>{title}</h3>
        <div className="stat-value">{value}</div>
        {subtitle && <p className="stat-subtitle">{subtitle}</p>}
      </div>
    </div>
  );

  const QuickAction = ({ icon: Icon, title, description, onClick, color = 'primary' }) => (
    <button className={`quick-action ${color}`} onClick={onClick}>
      <div className="action-icon">
        <Icon size={20} />
      </div>
      <div className="action-content">
        <h4>{title}</h4>
        <p>{description}</p>
      </div>
    </button>
  );

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>جاري تحميل لوحة التحكم...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* ترحيب */}
      <div className="welcome-section">
        <div className="welcome-content">
          <h1>مرحباً، {user?.full_name}</h1>
          <p>
            {user?.department && `${user.department} - `}
            {user?.position || 'موظف'}
          </p>
        </div>
        <div className="welcome-time">
          <Clock size={16} />
          <span>{new Date().toLocaleDateString('ar-SA')}</span>
        </div>
      </div>

      {/* الإحصائيات الرئيسية */}
      <div className="stats-grid">
        <StatCard
          icon={Link}
          title="إجمالي الروابط"
          value={stats.totalUrls}
          subtitle="الروابط المنشأة"
          color="primary"
        />
        <StatCard
          icon={MousePointer}
          title="إجمالي النقرات"
          value={stats.totalClicks}
          subtitle="النقرات الكلية"
          color="success"
        />
        <StatCard
          icon={TrendingUp}
          title="النقرات الحديثة"
          value={stats.recentClicks}
          subtitle="آخر 30 يوم"
          color="info"
        />
        <StatCard
          icon={BarChart3}
          title="متوسط النقرات"
          value={stats.totalUrls > 0 ? Math.round(stats.totalClicks / stats.totalUrls) : 0}
          subtitle="لكل رابط"
          color="warning"
        />
      </div>

      {/* الإجراءات السريعة */}
      <div className="quick-actions-section">
        <h2>الإجراءات السريعة</h2>
        <div className="quick-actions-grid">
          <QuickAction
            icon={Plus}
            title="إنشاء رابط جديد"
            description="اختصر رابط جديد بسرعة"
            onClick={() => {/* سيتم تنفيذه لاحقاً */}}
            color="primary"
          />
          <QuickAction
            icon={BarChart3}
            title="عرض التقارير"
            description="اطلع على الإحصائيات التفصيلية"
            onClick={() => {/* سيتم تنفيذه لاحقاً */}}
            color="info"
          />
          <QuickAction
            icon={Globe}
            title="إدارة الروابط"
            description="تحرير وإدارة الروابط الموجودة"
            onClick={() => {/* سيتم تنفيذه لاحقاً */}}
            color="success"
          />
        </div>
      </div>

      {/* الروابط الحديثة */}
      <div className="recent-urls-section">
        <div className="section-header">
          <h2>الروابط الحديثة</h2>
          <Button variant="outline" size="sm">
            عرض الكل
          </Button>
        </div>
        
        {recentUrls.length > 0 ? (
          <div className="recent-urls-list">
            {recentUrls.map((url) => (
              <div key={url.id} className="url-item">
                <div className="url-info">
                  <div className="url-title">
                    {url.title || url.original_url}
                  </div>
                  <div className="url-details">
                    <span className="short-url">rfah.me/{url.short_code}</span>
                    <span className="url-clicks">{url.clicks} نقرة</span>
                    <span className="url-date">
                      {new Date(url.created_at).toLocaleDateString('ar-SA')}
                    </span>
                  </div>
                </div>
                <div className="url-actions">
                  <Button variant="ghost" size="sm">
                    نسخ
                  </Button>
                  <Button variant="ghost" size="sm">
                    إحصائيات
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Link size={48} />
            <h3>لا توجد روابط بعد</h3>
            <p>ابدأ بإنشاء أول رابط مختصر لك</p>
            <Button>
              <Plus size={16} />
              إنشاء رابط جديد
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

