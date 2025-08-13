import React from 'react';
import { 
  Home, 
  Link, 
  BarChart3, 
  Users, 
  Shield, 
  Settings,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const Sidebar = ({ user, currentPage, onPageChange, isOpen, onClose }) => {
  const menuItems = [
    {
      id: 'dashboard',
      label: 'لوحة التحكم',
      icon: Home,
      permission: null // متاح للجميع
    },
    {
      id: 'urls',
      label: 'إدارة الروابط',
      icon: Link,
      permission: 'urls.view_own'
    },
    {
      id: 'analytics',
      label: 'التقارير والإحصائيات',
      icon: BarChart3,
      permission: 'reports.view_own'
    },
    {
      id: 'users',
      label: 'إدارة المستخدمين',
      icon: Users,
      permission: 'users.view'
    },
    {
      id: 'roles',
      label: 'إدارة الأدوار',
      icon: Shield,
      permission: 'roles.view'
    },
    {
      id: 'settings',
      label: 'الإعدادات',
      icon: Settings,
      permission: null // متاح للجميع
    }
  ];

  const hasPermission = (permission) => {
    if (!permission) return true; // إذا لم تكن هناك صلاحية مطلوبة
    if (user?.is_admin) return true; // المدير له جميع الصلاحيات
    return user?.permissions?.includes(permission) || false;
  };

  const filteredMenuItems = menuItems.filter(item => hasPermission(item.permission));

  return (
    <>
      {/* خلفية شفافة للموبايل */}
      {isOpen && (
        <div className="sidebar-overlay" onClick={onClose}></div>
      )}
      
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>القائمة الرئيسية</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="close-btn"
          >
            <X size={18} />
          </Button>
        </div>

        <nav className="sidebar-nav">
          {filteredMenuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => {
                  onPageChange(item.id);
                  onClose(); // إغلاق الشريط الجانبي في الموبايل
                }}
                className={`nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-summary">
            <div className="user-stats">
              <div className="stat">
                <span className="stat-label">الروابط</span>
                <span className="stat-value">{user?.urls_count || 0}</span>
              </div>
              <div className="stat">
                <span className="stat-label">النقرات</span>
                <span className="stat-value">-</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;

