// rfah-frontend/src/components/Login.jsx
import React, { useState } from 'react';
import { Eye, EyeOff, LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    identifier: '',   // <-- بدل username
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function safeParseJSON(response) {
    const ct = response.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      try {
        return await response.json();
      } catch {
        return null;
      }
    }
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // مهم لحفظ الجلسة
        body: JSON.stringify({
          identifier: formData.identifier?.trim(),
          password: formData.password
        })
      });

      const data = await safeParseJSON(res);

      if (!res.ok) {
        // أخطاء شائعة مع رسائل عربية
        if (res.status === 400) setError('الرجاء إدخال اسم المستخدم/البريد وكلمة المرور');
        else if (res.status === 401) setError('بيانات الدخول غير صحيحة');
        else setError(data?.error || 'خطأ في الاتصال بالخادم');
        return;
      }

      // شكل رد الخادم: { ok: true, user: {..} }
      if (data?.ok && data.user) {
        onLogin?.(data.user);
      } else {
        setError(data?.error || 'خطأ في تسجيل الدخول');
      }
    } catch {
      setError('تعذر الاتصال بالخادم. حاول لاحقًا.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-pattern"></div>
      </div>

      <div className="login-card">
        <div className="login-header">
          {/* ملاحظة: ضع الشعار داخل مجلد public باسم rafah-logo.png
              ثم استخدم /rafah-logo.png كما بالأسفل */}
          <img
            src="/rafah-logo.png"
            alt="جمعية رفاه"
            className="login-logo"
          />
          <h1>نظام رفاه</h1>
          <p>لإدارة الروابط المختصرة</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="identifier">اسم المستخدم أو البريد الإلكتروني</label>
            <input
              type="text"
              id="identifier"
              name="identifier"
              value={formData.identifier}
              onChange={handleChange}
              required
              placeholder="أدخل اسم المستخدم أو البريد الإلكتروني"
              className="form-input"
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">كلمة المرور</label>
            <div className="password-input">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                placeholder="أدخل كلمة المرور"
                className="form-input"
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="password-toggle"
                aria-label={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <Button type="submit" disabled={loading} className="login-button">
            {loading ? <div className="loading-spinner small"></div> : (<><LogIn size={18} /> تسجيل الدخول</>)}
          </Button>
        </form>

        <div className="login-footer">
          <p>© 2025 جمعية رفاه للأرامل والمطلقات</p>
          <p>جميع الحقوق محفوظة</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
