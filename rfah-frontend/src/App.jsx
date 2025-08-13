import React, { useState, useEffect } from 'react';
import './App.css';

// مكونات الواجهة
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import URLManager from './components/URLManager';
import Analytics from './components/Analytics';
import UserManagement from './components/UserManagement';
import RoleManagement from './components/RoleManagement';
import Settings from './components/Settings';
import Login from './components/Login';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // التحقق من حالة تسجيل الدخول عند تحميل التطبيق
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await fetch('/api/auth/check-session');
      const data = await response.json();
      
      if (data.authenticated) {
        setCurrentUser(data.user);
      }
    } catch (error) {
      console.error('خطأ في التحقق من حالة المصادقة:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (user) => {
    setCurrentUser(user);
    setCurrentPage('dashboard');
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      setCurrentUser(null);
      setCurrentPage('dashboard');
    } catch (error) {
      console.error('خطأ في تسجيل الخروج:', error);
    }
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard user={currentUser} />;
      case 'urls':
        return <URLManager user={currentUser} />;
      case 'analytics':
        return <Analytics user={currentUser} />;
      case 'users':
        return <UserManagement user={currentUser} />;
      case 'roles':
        return <RoleManagement user={currentUser} />;
      case 'settings':
        return <Settings user={currentUser} />;
      default:
        return <Dashboard user={currentUser} />;
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>جاري التحميل...</p>
      </div>
    );
  }

  if (!currentUser) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app" dir="rtl">
      <Header 
        user={currentUser}
        onLogout={handleLogout}
        onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      
      <div className="app-body">
        <Sidebar
          user={currentUser}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        
        <main className={`main-content ${sidebarOpen ? 'sidebar-open' : ''}`}>
          <div className="content-wrapper">
            {renderCurrentPage()}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
