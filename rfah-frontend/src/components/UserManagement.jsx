import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  RotateCcw,
  Shield,
  Mail,
  Phone,
  Building,
  UserCheck,
  UserX
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const UserManagement = ({ user }) => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showDeleted, setShowDeleted] = useState(false);

  useEffect(() => {
    loadUsers();
    loadRoles();
  }, [showDeleted]);

  const loadUsers = async () => {
    try {
      const response = await fetch(`/api/admin/users?include_deleted=${showDeleted}`);
      const data = await response.json();
      
      if (data.success) {
        setUsers(data.users);
      }
    } catch (error) {
      console.error('خطأ في جلب المستخدمين:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRoles = async () => {
    try {
      const response = await fetch('/api/admin/roles');
      const data = await response.json();
      
      if (data.success) {
        setRoles(data.roles);
      }
    } catch (error) {
      console.error('خطأ في جلب الأدوار:', error);
    }
  };

  const deleteUser = async (userId) => {
    if (!confirm('هل أنت متأكد من حذف هذا المستخدم؟')) return;

    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        loadUsers();
      }
    } catch (error) {
      console.error('خطأ في حذف المستخدم:', error);
    }
  };

  const restoreUser = async (userId) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}/restore`, {
        method: 'POST'
      });
      
      if (response.ok) {
        loadUsers();
      }
    } catch (error) {
      console.error('خطأ في استعادة المستخدم:', error);
    }
  };

  const filteredUsers = users.filter(user =>
    user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const UserCard = ({ userData }) => (
    <div className={`user-card ${userData.deleted_at ? 'deleted' : ''}`}>
      <div className="user-header">
        <div className="user-avatar">
          <Users size={24} />
        </div>
        <div className="user-info">
          <h3>{userData.full_name}</h3>
          <p className="username">@{userData.username}</p>
        </div>
        <div className="user-status">
          {userData.deleted_at ? (
            <span className="status deleted">محذوف</span>
          ) : userData.is_active ? (
            <span className="status active">نشط</span>
          ) : (
            <span className="status inactive">غير نشط</span>
          )}
        </div>
      </div>

      <div className="user-details">
        <div className="detail-item">
          <Mail size={16} />
          <span>{userData.email}</span>
        </div>
        {userData.phone && (
          <div className="detail-item">
            <Phone size={16} />
            <span>{userData.phone}</span>
          </div>
        )}
        {userData.department && (
          <div className="detail-item">
            <Building size={16} />
            <span>{userData.department}</span>
          </div>
        )}
        <div className="detail-item">
          <Shield size={16} />
          <span>
            {userData.is_admin 
              ? 'مدير النظام' 
              : userData.role?.display_name || 'بدون دور'
            }
          </span>
        </div>
      </div>

      <div className="user-stats">
        <div className="stat">
          <span className="stat-value">{userData.urls_count || 0}</span>
          <span className="stat-label">رابط</span>
        </div>
        <div className="stat">
          <span className="stat-value">
            {userData.last_login 
              ? new Date(userData.last_login).toLocaleDateString('ar-SA')
              : 'لم يسجل دخول'
            }
          </span>
          <span className="stat-label">آخر دخول</span>
        </div>
      </div>

      <div className="user-actions">
        {userData.deleted_at ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => restoreUser(userData.id)}
          >
            <RotateCcw size={16} />
            استعادة
          </Button>
        ) : (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedUser(userData)}
            >
              <Edit size={16} />
              تحرير
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteUser(userData.id)}
              className="delete-btn"
            >
              <Trash2 size={16} />
              حذف
            </Button>
          </>
        )}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>جاري تحميل المستخدمين...</p>
      </div>
    );
  }

  return (
    <div className="user-management">
      {/* رأس الصفحة */}
      <div className="page-header">
        <div className="header-content">
          <h1>إدارة المستخدمين</h1>
          <p>إدارة حسابات المستخدمين وصلاحياتهم</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          إضافة مستخدم جديد
        </Button>
      </div>

      {/* شريط الأدوات */}
      <div className="toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="البحث عن المستخدمين..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="toolbar-actions">
          <Button
            variant={showDeleted ? 'default' : 'outline'}
            onClick={() => setShowDeleted(!showDeleted)}
          >
            {showDeleted ? (
              <>
                <UserCheck size={16} />
                المستخدمين النشطين
              </>
            ) : (
              <>
                <UserX size={16} />
                المستخدمين المحذوفين
              </>
            )}
          </Button>
        </div>
      </div>

      {/* قائمة المستخدمين */}
      <div className="users-container">
        {filteredUsers.length > 0 ? (
          <div className="users-grid">
            {filteredUsers.map((userData) => (
              <UserCard key={userData.id} userData={userData} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Users size={48} />
            <h3>لا توجد مستخدمين</h3>
            <p>
              {searchTerm 
                ? 'لم يتم العثور على مستخدمين يطابقون البحث'
                : showDeleted 
                  ? 'لا توجد مستخدمين محذوفين'
                  : 'لا توجد مستخدمين مسجلين بعد'
              }
            </p>
          </div>
        )}
      </div>

      {/* نافذة إنشاء مستخدم جديد */}
      {showCreateModal && (
        <CreateUserModal
          roles={roles}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadUsers();
          }}
        />
      )}

      {/* نافذة تحرير المستخدم */}
      {selectedUser && (
        <EditUserModal
          user={selectedUser}
          roles={roles}
          onClose={() => setSelectedUser(null)}
          onSuccess={() => {
            setSelectedUser(null);
            loadUsers();
          }}
        />
      )}
    </div>
  );
};

// مكون نافذة إنشاء مستخدم جديد
const CreateUserModal = ({ roles, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    phone: '',
    department: '',
    position: '',
    role_id: '',
    is_admin: false
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/admin/users', {
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
        setError(data.error || 'خطأ في إنشاء المستخدم');
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
          <h2>إضافة مستخدم جديد</h2>
          <Button variant="ghost" onClick={onClose}>×</Button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-row">
            <div className="form-group">
              <label>اسم المستخدم *</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({...formData, username: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>البريد الإلكتروني *</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>كلمة المرور *</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              required
            />
          </div>

          <div className="form-group">
            <label>الاسم الكامل *</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>رقم الهاتف</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>القسم</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({...formData, department: e.target.value})}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>المنصب</label>
              <input
                type="text"
                value={formData.position}
                onChange={(e) => setFormData({...formData, position: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>الدور</label>
              <select
                value={formData.role_id}
                onChange={(e) => setFormData({...formData, role_id: e.target.value})}
              >
                <option value="">اختر الدور</option>
                {roles.map(role => (
                  <option key={role.id} value={role.id}>
                    {role.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.is_admin}
                onChange={(e) => setFormData({...formData, is_admin: e.target.checked})}
              />
              مدير النظام
            </label>
          </div>

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose}>
              إلغاء
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'جاري الإنشاء...' : 'إنشاء المستخدم'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// مكون نافذة تحرير المستخدم
const EditUserModal = ({ user: userData, roles, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    full_name: userData.full_name || '',
    email: userData.email || '',
    phone: userData.phone || '',
    department: userData.department || '',
    position: userData.position || '',
    role_id: userData.role_id || '',
    is_admin: userData.is_admin || false,
    is_active: userData.is_active || false
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`/api/admin/users/${userData.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        onSuccess();
      } else {
        setError(data.error || 'خطأ في تحديث المستخدم');
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
          <h2>تحرير المستخدم</h2>
          <Button variant="ghost" onClick={onClose}>×</Button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label>اسم المستخدم</label>
            <input
              type="text"
              value={userData.username}
              disabled
              className="disabled"
            />
          </div>

          <div className="form-group">
            <label>الاسم الكامل *</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              required
            />
          </div>

          <div className="form-group">
            <label>البريد الإلكتروني *</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>رقم الهاتف</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>القسم</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({...formData, department: e.target.value})}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>المنصب</label>
              <input
                type="text"
                value={formData.position}
                onChange={(e) => setFormData({...formData, position: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>الدور</label>
              <select
                value={formData.role_id}
                onChange={(e) => setFormData({...formData, role_id: e.target.value})}
              >
                <option value="">اختر الدور</option>
                {roles.map(role => (
                  <option key={role.id} value={role.id}>
                    {role.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.is_admin}
                onChange={(e) => setFormData({...formData, is_admin: e.target.checked})}
              />
              مدير النظام
            </label>
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
              />
              حساب نشط
            </label>
          </div>

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose}>
              إلغاء
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'جاري التحديث...' : 'تحديث المستخدم'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserManagement;

