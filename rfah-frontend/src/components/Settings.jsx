import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  User, 
  Lock, 
  Globe, 
  Bell,
  Save,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const Settings = ({ user }) => {
  const [activeTab, setActiveTab] = useState('profile');
  const [profileData, setProfileData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    department: user?.department || '',
    position: user?.position || ''
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const tabs = [
    {
      id: 'profile',
      label: 'الملف الشخصي',
      icon: User
    },
    {
      id: 'password',
      label: 'كلمة المرور',
      icon: Lock
    },
    {
      id: 'notifications',
      label: 'الإشعارات',
      icon: Bell
    },
    {
      id: 'system',
      label: 'إعدادات النظام',
      icon: SettingsIcon,
      adminOnly: true
    }
  ];

  const filteredTabs = tabs.filter(tab => 
    !tab.adminOnly || user?.is_admin || user?.permissions?.includes('system.settings')
  );

  const updateProfile = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });

      const data = await response.json();

      if (data.success) {
        setMessage('تم تحديث الملف الشخصي بنجاح');
      } else {
        setError(data.error || 'خطأ في تحديث الملف الشخصي');
      }
    } catch (error) {
      setError('خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  const updatePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    if (passwordData.new_password !== passwordData.confirm_password) {
      setError('كلمة المرور الجديدة وتأكيدها غير متطابقتين');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_password: passwordData.current_password,
          new_password: passwordData.new_password
        }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage('تم تحديث كلمة المرور بنجاح');
        setPasswordData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      } else {
        setError(data.error || 'خطأ في تحديث كلمة المرور');
      }
    } catch (error) {
      setError('خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  const ProfileTab = () => (
    <div className="settings-tab">
      <div className="tab-header">
        <h2>الملف الشخصي</h2>
        <p>تحديث معلوماتك الشخصية</p>
      </div>

      <form onSubmit={updateProfile} className="settings-form">
        <div className="form-group">
          <label>الاسم الكامل</label>
          <input
            type="text"
            value={profileData.full_name}
            onChange={(e) => setProfileData({...profileData, full_name: e.target.value})}
            required
          />
        </div>

        <div className="form-group">
          <label>البريد الإلكتروني</label>
          <input
            type="email"
            value={profileData.email}
            onChange={(e) => setProfileData({...profileData, email: e.target.value})}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>رقم الهاتف</label>
            <input
              type="tel"
              value={profileData.phone}
              onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
            />
          </div>
          <div className="form-group">
            <label>القسم</label>
            <input
              type="text"
              value={profileData.department}
              onChange={(e) => setProfileData({...profileData, department: e.target.value})}
            />
          </div>
        </div>

        <div className="form-group">
          <label>المنصب</label>
          <input
            type="text"
            value={profileData.position}
            onChange={(e) => setProfileData({...profileData, position: e.target.value})}
          />
        </div>

        <div className="form-actions">
          <Button type="submit" disabled={loading}>
            <Save size={16} />
            {loading ? 'جاري الحفظ...' : 'حفظ التغييرات'}
          </Button>
        </div>
      </form>
    </div>
  );

  const PasswordTab = () => (
    <div className="settings-tab">
      <div className="tab-header">
        <h2>تغيير كلمة المرور</h2>
        <p>تحديث كلمة المرور الخاصة بك</p>
      </div>

      <form onSubmit={updatePassword} className="settings-form">
        <div className="form-group">
          <label>كلمة المرور الحالية</label>
          <div className="password-input">
            <input
              type={showPasswords.current ? 'text' : 'password'}
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({...passwordData, current_password: e.target.value})}
              required
            />
            <button
              type="button"
              onClick={() => setShowPasswords({...showPasswords, current: !showPasswords.current})}
              className="password-toggle"
            >
              {showPasswords.current ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>كلمة المرور الجديدة</label>
          <div className="password-input">
            <input
              type={showPasswords.new ? 'text' : 'password'}
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
              required
              minLength="6"
            />
            <button
              type="button"
              onClick={() => setShowPasswords({...showPasswords, new: !showPasswords.new})}
              className="password-toggle"
            >
              {showPasswords.new ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>تأكيد كلمة المرور الجديدة</label>
          <div className="password-input">
            <input
              type={showPasswords.confirm ? 'text' : 'password'}
              value={passwordData.confirm_password}
              onChange={(e) => setPasswordData({...passwordData, confirm_password: e.target.value})}
              required
              minLength="6"
            />
            <button
              type="button"
              onClick={() => setShowPasswords({...showPasswords, confirm: !showPasswords.confirm})}
              className="password-toggle"
            >
              {showPasswords.confirm ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <div className="password-requirements">
          <h4>متطلبات كلمة المرور:</h4>
          <ul>
            <li>يجب أن تكون 6 أحرف على الأقل</li>
            <li>يُفضل استخدام مزيج من الأحرف والأرقام</li>
            <li>تجنب استخدام معلومات شخصية</li>
          </ul>
        </div>

        <div className="form-actions">
          <Button type="submit" disabled={loading}>
            <Save size={16} />
            {loading ? 'جاري التحديث...' : 'تحديث كلمة المرور'}
          </Button>
        </div>
      </form>
    </div>
  );

  const NotificationsTab = () => (
    <div className="settings-tab">
      <div className="tab-header">
        <h2>إعدادات الإشعارات</h2>
        <p>تخصيص الإشعارات التي تريد تلقيها</p>
      </div>

      <div className="notifications-settings">
        <div className="notification-group">
          <h3>إشعارات الروابط</h3>
          <div className="notification-item">
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              إشعار عند إنشاء رابط جديد
            </label>
          </div>
          <div className="notification-item">
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              إشعار عند وصول الرابط لعدد نقرات معين
            </label>
          </div>
        </div>

        <div className="notification-group">
          <h3>إشعارات النظام</h3>
          <div className="notification-item">
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              إشعارات الأمان والتحديثات
            </label>
          </div>
          <div className="notification-item">
            <label className="checkbox-label">
              <input type="checkbox" />
              إشعارات التقارير الدورية
            </label>
          </div>
        </div>

        <div className="form-actions">
          <Button>
            <Save size={16} />
            حفظ إعدادات الإشعارات
          </Button>
        </div>
      </div>
    </div>
  );

  const SystemTab = () => (
    <div className="settings-tab">
      <div className="tab-header">
        <h2>إعدادات النظام</h2>
        <p>إعدادات عامة للنظام (للمدراء فقط)</p>
      </div>

      <div className="system-settings">
        <div className="setting-group">
          <h3>إعدادات عامة</h3>
          <div className="setting-item">
            <label>اسم النظام</label>
            <input type="text" defaultValue="نظام رفاه" />
          </div>
          <div className="setting-item">
            <label>النطاق الأساسي</label>
            <input type="text" defaultValue="rfah.me" />
          </div>
        </div>

        <div className="setting-group">
          <h3>إعدادات الأمان</h3>
          <div className="setting-item">
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              تفعيل المصادقة الثنائية
            </label>
          </div>
          <div className="setting-item">
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              تسجيل جميع العمليات
            </label>
          </div>
        </div>

        <div className="setting-group">
          <h3>إعدادات الروابط</h3>
          <div className="setting-item">
            <label>الحد الأقصى للروابط لكل مستخدم</label>
            <input type="number" defaultValue="100" />
          </div>
          <div className="setting-item">
            <label>مدة انتهاء الصلاحية الافتراضية (بالأيام)</label>
            <input type="number" defaultValue="365" />
          </div>
        </div>

        <div className="form-actions">
          <Button>
            <Save size={16} />
            حفظ إعدادات النظام
          </Button>
        </div>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileTab />;
      case 'password':
        return <PasswordTab />;
      case 'notifications':
        return <NotificationsTab />;
      case 'system':
        return <SystemTab />;
      default:
        return <ProfileTab />;
    }
  };

  return (
    <div className="settings">
      {/* رأس الصفحة */}
      <div className="page-header">
        <div className="header-content">
          <h1>الإعدادات</h1>
          <p>إدارة إعدادات حسابك والنظام</p>
        </div>
      </div>

      {/* الرسائل */}
      {message && (
        <div className="success-message">
          {message}
        </div>
      )}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="settings-container">
        {/* التبويبات */}
        <div className="settings-sidebar">
          <nav className="settings-nav">
            {filteredTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
                >
                  <Icon size={20} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* محتوى التبويب */}
        <div className="settings-content">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default Settings;

