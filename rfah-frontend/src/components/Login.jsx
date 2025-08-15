import React, { useEffect, useState } from 'react';
import { Eye, EyeOff, LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // خريطة رسائل الأخطاء القادمة من الباك
  const errorMessage = (code) => {
    switch (code) {
      case 'missing_fields':
        return 'الرجاء إدخال اسم المستخدم/الإيميل وكلمة المرور';
      case 'invalid_credentials':
        return 'بيانات الدخول غير صحيحة';
      case 'invalid_json':
        return 'صيغة الطلب غير صحيحة';
      default:
        return 'خطأ في تسجيل الدخول';
    }
  };

  // فحص الجلسة عند فتح الصفحة
  useEffect(() => {
    let isMounted = true;
    (async () => {
      try {
        const res = await fetch('/api/auth/check-session', {
          method: 'GET',
          credentials: 'include',
        });
        if (!isMounted) return;
        if (res.ok) {
          const data = await res.json();
          if (data?.ok && data?.user) {
            onLogin?.(data.user);
          }
        }
      } catch {
        /* نتجاهل الخطأ هنا */
      }
    })();
    return () => { isMounted = false; };
  }, [onLogin]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // مهم للجلسة
        body: JSON.stringify({
          identifier: formData.username?.trim(), // اسم المستخدم أو الإيميل
          password: formData.password,
        }),
      });

      // حاول قراءة JSON حتى لو كان status خطأ
      let data = {};
      try {
        data = await response.json();
      } catch {
        /* قد يرجع الباك HTML في حالة خطأ غير متوقع */
      }

      if (response.ok && data?.success) {
        onLogin?.(data.user);
      } else {
        setError(errorMessage(data?.error));
      }
    } catch {
      setError('خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-pattern"></div>
      </div>

      <div className="login-card">
        <div className="login-header">
          {/* ضَع الصورة في public/rafah-logo.png */}
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
            <label htmlFor="username">اسم المستخدم أو البريد الإلكتروني</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="أدخل اسم المستخدم أو البريد الإلكتروني"
              className="form-input"
              autoComplete="username"
              inputMode="email"
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
                onClick={() => setShowPassword((v) => !v)}
                className="password-toggle"
                aria-label={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="login-button"
          >
            {loading ? (
              <div className="loading-spinner small" />
            ) : (
              <>
                <LogIn size={18} />
                <span className="ms-2">تسجيل الدخول</span>
              </>
            )}
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
