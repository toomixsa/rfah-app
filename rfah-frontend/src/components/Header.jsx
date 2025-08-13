import React from 'react';
import { Menu, Bell, User, LogOut, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Header = ({ user, onLogout, onMenuToggle }) => {
  return (
    <header className="header">
      <div className="header-content">
        {/* الجانب الأيمن - الشعار والقائمة */}
        <div className="header-right">
          <Button
            variant="ghost"
            size="sm"
            onClick={onMenuToggle}
            className="menu-toggle"
          >
            <Menu size={20} />
          </Button>
          
          <div className="logo-section">
            <img 
              src="/assets/rafah-logo.png" 
              alt="جمعية رفاه" 
              className="logo"
            />
            <div className="logo-text">
              <h1>نظام رفاه</h1>
              <span>لإدارة الروابط المختصرة</span>
            </div>
          </div>
        </div>

        {/* الجانب الأيسر - معلومات المستخدم */}
        <div className="header-left">
          <div className="notifications">
            <Button variant="ghost" size="sm">
              <Bell size={18} />
            </Button>
          </div>

          <div className="user-menu">
            <div className="user-info">
              <span className="user-name">{user?.full_name}</span>
              <span className="user-role">
                {user?.is_admin ? 'مدير النظام' : user?.role?.display_name || 'موظف'}
              </span>
            </div>
            
            <div className="user-avatar">
              <User size={20} />
            </div>

            <div className="user-dropdown">
              <Button variant="ghost" size="sm">
                <Settings size={16} />
                الإعدادات
              </Button>
              <Button variant="ghost" size="sm" onClick={onLogout}>
                <LogOut size={16} />
                تسجيل الخروج
              </Button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;

