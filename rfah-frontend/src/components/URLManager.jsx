import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Search, 
  Filter,
  Copy,
  Edit,
  Trash2,
  BarChart3,
  ExternalLink,
  Calendar,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const URLManager = ({ user }) => {
  const [urls, setUrls] = useState([]);
  const [filteredUrls, setFilteredUrls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedUrl, setSelectedUrl] = useState(null);

  useEffect(() => {
    loadUrls();
  }, []);

  useEffect(() => {
    filterUrls();
  }, [urls, searchTerm, filterStatus]);

  const loadUrls = async () => {
    try {
      const response = await fetch('/api/urls/my-urls');
      const data = await response.json();
      
      if (data.success) {
        setUrls(data.urls);
      }
    } catch (error) {
      console.error('خطأ في جلب الروابط:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterUrls = () => {
    let filtered = urls;

    // تصفية حسب البحث
    if (searchTerm) {
      filtered = filtered.filter(url => 
        url.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        url.original_url.toLowerCase().includes(searchTerm.toLowerCase()) ||
        url.short_code.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // تصفية حسب الحالة
    if (filterStatus !== 'all') {
      filtered = filtered.filter(url => {
        switch (filterStatus) {
          case 'active':
            return url.is_active && !url.is_expired;
          case 'inactive':
            return !url.is_active;
          case 'expired':
            return url.is_expired;
          default:
            return true;
        }
      });
    }

    setFilteredUrls(filtered);
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      // إظهار رسالة نجاح
    } catch (error) {
      console.error('خطأ في النسخ:', error);
    }
  };

  const deleteUrl = async (urlId) => {
    if (!confirm('هل أنت متأكد من حذف هذا الرابط؟')) return;

    try {
      const response = await fetch(`/api/urls/urls/${urlId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        loadUrls(); // إعادة تحميل القائمة
      }
    } catch (error) {
      console.error('خطأ في حذف الرابط:', error);
    }
  };

  const URLCard = ({ url }) => (
    <div className="url-card">
      <div className="url-header">
        <div className="url-title">
          <h3>{url.title || 'بدون عنوان'}</h3>
          <div className="url-status">
            {url.is_expired ? (
              <span className="status expired">منتهي الصلاحية</span>
            ) : url.is_active ? (
              <span className="status active">نشط</span>
            ) : (
              <span className="status inactive">غير نشط</span>
            )}
          </div>
        </div>
        <div className="url-actions">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => copyToClipboard(`https://rfah.me/${url.short_code}`)}
          >
            <Copy size={16} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedUrl(url)}
          >
            <BarChart3 size={16} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {/* فتح نافذة التحرير */}}
          >
            <Edit size={16} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => deleteUrl(url.id)}
            className="delete-btn"
          >
            <Trash2 size={16} />
          </Button>
        </div>
      </div>

      <div className="url-content">
        <div className="url-links">
          <div className="short-url">
            <span className="label">الرابط المختصر:</span>
            <a 
              href={`https://rfah.me/${url.short_code}`}
              target="_blank"
              rel="noopener noreferrer"
              className="link"
            >
              rfah.me/{url.short_code}
              <ExternalLink size={14} />
            </a>
          </div>
          <div className="original-url">
            <span className="label">الرابط الأصلي:</span>
            <span className="url-text" title={url.original_url}>
              {url.original_url}
            </span>
          </div>
        </div>

        {url.description && (
          <div className="url-description">
            <span className="label">الوصف:</span>
            <p>{url.description}</p>
          </div>
        )}
      </div>

      <div className="url-footer">
        <div className="url-stats">
          <div className="stat">
            <span className="stat-value">{url.clicks}</span>
            <span className="stat-label">نقرة</span>
          </div>
          <div className="stat">
            <span className="stat-value">
              {new Date(url.created_at).toLocaleDateString('ar-SA')}
            </span>
            <span className="stat-label">تاريخ الإنشاء</span>
          </div>
          {url.expires_at && (
            <div className="stat">
              <span className="stat-value">
                {new Date(url.expires_at).toLocaleDateString('ar-SA')}
              </span>
              <span className="stat-label">تاريخ الانتهاء</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>جاري تحميل الروابط...</p>
      </div>
    );
  }

  return (
    <div className="url-manager">
      {/* رأس الصفحة */}
      <div className="page-header">
        <div className="header-content">
          <h1>إدارة الروابط</h1>
          <p>إدارة وتتبع جميع الروابط المختصرة الخاصة بك</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          إنشاء رابط جديد
        </Button>
      </div>

      {/* شريط البحث والتصفية */}
      <div className="toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="البحث في الروابط..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filters">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="filter-select"
          >
            <option value="all">جميع الروابط</option>
            <option value="active">الروابط النشطة</option>
            <option value="inactive">الروابط غير النشطة</option>
            <option value="expired">الروابط المنتهية الصلاحية</option>
          </select>
        </div>
      </div>

      {/* قائمة الروابط */}
      <div className="urls-container">
        {filteredUrls.length > 0 ? (
          <div className="urls-grid">
            {filteredUrls.map((url) => (
              <URLCard key={url.id} url={url} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            {searchTerm || filterStatus !== 'all' ? (
              <>
                <Search size={48} />
                <h3>لا توجد نتائج</h3>
                <p>لم يتم العثور على روابط تطابق معايير البحث</p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearchTerm('');
                    setFilterStatus('all');
                  }}
                >
                  مسح البحث
                </Button>
              </>
            ) : (
              <>
                <Plus size={48} />
                <h3>لا توجد روابط بعد</h3>
                <p>ابدأ بإنشاء أول رابط مختصر لك</p>
                <Button onClick={() => setShowCreateModal(true)}>
                  <Plus size={16} />
                  إنشاء رابط جديد
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* نافذة إنشاء رابط جديد */}
      {showCreateModal && (
        <CreateURLModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadUrls();
          }}
        />
      )}

      {/* نافذة إحصائيات الرابط */}
      {selectedUrl && (
        <URLStatsModal
          url={selectedUrl}
          onClose={() => setSelectedUrl(null)}
        />
      )}
    </div>
  );
};

// مكون نافذة إنشاء رابط جديد
const CreateURLModal = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    original_url: '',
    custom_alias: '',
    title: '',
    description: '',
    expires_at: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/urls/shorten', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        onSuccess();
      } else {
        setError(data.error || 'خطأ في إنشاء الرابط');
      }
    } catch (error) {
      setError('خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2>إنشاء رابط جديد</h2>
          <Button variant="ghost" onClick={onClose}>
            ×
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && (
            <div className="error-message">{error}</div>
          )}

          <div className="form-group">
            <label>الرابط الأصلي *</label>
            <input
              type="url"
              value={formData.original_url}
              onChange={(e) => setFormData({...formData, original_url: e.target.value})}
              placeholder="https://example.com"
              required
            />
          </div>

          <div className="form-group">
            <label>الاسم المخصص (اختياري)</label>
            <input
              type="text"
              value={formData.custom_alias}
              onChange={(e) => setFormData({...formData, custom_alias: e.target.value})}
              placeholder="my-link"
            />
          </div>

          <div className="form-group">
            <label>العنوان (اختياري)</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              placeholder="عنوان وصفي للرابط"
            />
          </div>

          <div className="form-group">
            <label>الوصف (اختياري)</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              placeholder="وصف مختصر للرابط"
              rows="3"
            />
          </div>

          <div className="form-group">
            <label>تاريخ انتهاء الصلاحية (اختياري)</label>
            <input
              type="datetime-local"
              value={formData.expires_at}
              onChange={(e) => setFormData({...formData, expires_at: e.target.value})}
            />
          </div>

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose}>
              إلغاء
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'جاري الإنشاء...' : 'إنشاء الرابط'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// مكون نافذة إحصائيات الرابط
const URLStatsModal = ({ url, onClose }) => {
  return (
    <div className="modal-overlay">
      <div className="modal large">
        <div className="modal-header">
          <h2>إحصائيات الرابط</h2>
          <Button variant="ghost" onClick={onClose}>
            ×
          </Button>
        </div>

        <div className="stats-content">
          <div className="stats-summary">
            <div className="stat-card">
              <h3>إجمالي النقرات</h3>
              <div className="stat-value">{url.clicks}</div>
            </div>
            <div className="stat-card">
              <h3>تاريخ الإنشاء</h3>
              <div className="stat-value">
                {new Date(url.created_at).toLocaleDateString('ar-SA')}
              </div>
            </div>
          </div>
          
          <p>المزيد من الإحصائيات التفصيلية ستكون متاحة قريباً...</p>
        </div>
      </div>
    </div>
  );
};

export default URLManager;

