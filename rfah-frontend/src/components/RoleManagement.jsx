import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Plus, 
  Edit, 
  Trash2, 
  RotateCcw,
  Users,
  Check,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const RoleManagement = ({ user }) => {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [showDeleted, setShowDeleted] = useState(false);

  useEffect(() => {
    loadRoles();
    loadPermissions();
  }, [showDeleted]);

  const loadRoles = async () => {
    try {
      const response = await fetch(`/api/admin/roles?include_deleted=${showDeleted}`);
      const data = await response.json();
      
      if (data.success) {
        setRoles(data.roles);
      }
    } catch (error) {
      console.error('خطأ في جلب الأدوار:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPermissions = async () => {
    try {
      const response = await fetch('/api/admin/permissions');
      const data = await response.json();
      
      if (data.success) {
        setPermissions(data.permissions);
      }
    } catch (error) {
      console.error('خطأ في جلب الصلاحيات:', error);
    }
  };

  const deleteRole = async (roleId) => {
    if (!confirm('هل أنت متأكد من حذف هذا الدور؟')) return;

    try {
      const response = await fetch(`/api/admin/roles/${roleId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        loadRoles();
      }
    } catch (error) {
      console.error('خطأ في حذف الدور:', error);
    }
  };

  const restoreRole = async (roleId) => {
    try {
      const response = await fetch(`/api/admin/roles/${roleId}/restore`, {
        method: 'POST'
      });
      
      if (response.ok) {
        loadRoles();
      }
    } catch (error) {
      console.error('خطأ في استعادة الدور:', error);
    }
  };

  const RoleCard = ({ role }) => (
    <div className={`role-card ${role.deleted_at ? 'deleted' : ''}`}>
      <div className="role-header">
        <div className="role-icon">
          <Shield size={24} />
        </div>
        <div className="role-info">
          <h3>{role.display_name}</h3>
          <p className="role-name">{role.name}</p>
        </div>
        <div className="role-status">
          {role.deleted_at ? (
            <span className="status deleted">محذوف</span>
          ) : role.is_active ? (
            <span className="status active">نشط</span>
          ) : (
            <span className="status inactive">غير نشط</span>
          )}
          {role.is_system && (
            <span className="status system">نظامي</span>
          )}
        </div>
      </div>

      <div className="role-description">
        <p>{role.description || 'لا يوجد وصف'}</p>
      </div>

      <div className="role-permissions">
        <h4>الصلاحيات ({role.permissions?.length || 0})</h4>
        <div className="permissions-preview">
          {role.permissions?.slice(0, 3).map(permission => (
            <span key={permission.id} className="permission-tag">
              {permission.display_name}
            </span>
          ))}
          {role.permissions?.length > 3 && (
            <span className="more-permissions">
              +{role.permissions.length - 3} أخرى
            </span>
          )}
        </div>
      </div>

      <div className="role-stats">
        <div className="stat">
          <Users size={16} />
          <span>0 مستخدم</span>
        </div>
        <div className="stat">
          <span>
            {new Date(role.created_at).toLocaleDateString('ar-SA')}
          </span>
        </div>
      </div>

      <div className="role-actions">
        {role.deleted_at ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => restoreRole(role.id)}
          >
            <RotateCcw size={16} />
            استعادة
          </Button>
        ) : (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedRole(role)}
              disabled={role.is_system}
            >
              <Edit size={16} />
              تحرير
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteRole(role.id)}
              className="delete-btn"
              disabled={role.is_system}
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
        <p>جاري تحميل الأدوار...</p>
      </div>
    );
  }

  return (
    <div className="role-management">
      {/* رأس الصفحة */}
      <div className="page-header">
        <div className="header-content">
          <h1>إدارة الأدوار والصلاحيات</h1>
          <p>إدارة أدوار المستخدمين وصلاحياتهم في النظام</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          إنشاء دور جديد
        </Button>
      </div>

      {/* شريط الأدوات */}
      <div className="toolbar">
        <div className="toolbar-info">
          <span>إجمالي الأدوار: {roles.length}</span>
        </div>
        <div className="toolbar-actions">
          <Button
            variant={showDeleted ? 'default' : 'outline'}
            onClick={() => setShowDeleted(!showDeleted)}
          >
            {showDeleted ? 'الأدوار النشطة' : 'الأدوار المحذوفة'}
          </Button>
        </div>
      </div>

      {/* قائمة الأدوار */}
      <div className="roles-container">
        {roles.length > 0 ? (
          <div className="roles-grid">
            {roles.map((role) => (
              <RoleCard key={role.id} role={role} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Shield size={48} />
            <h3>لا توجد أدوار</h3>
            <p>
              {showDeleted 
                ? 'لا توجد أدوار محذوفة'
                : 'لا توجد أدوار منشأة بعد'
              }
            </p>
          </div>
        )}
      </div>

      {/* نافذة إنشاء دور جديد */}
      {showCreateModal && (
        <CreateRoleModal
          permissions={permissions}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadRoles();
          }}
        />
      )}

      {/* نافذة تحرير الدور */}
      {selectedRole && (
        <EditRoleModal
          role={selectedRole}
          permissions={permissions}
          onClose={() => setSelectedRole(null)}
          onSuccess={() => {
            setSelectedRole(null);
            loadRoles();
          }}
        />
      )}
    </div>
  );
};

// مكون نافذة إنشاء دور جديد
const CreateRoleModal = ({ permissions, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    permission_ids: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/admin/roles', {
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
        setError(data.error || 'خطأ في إنشاء الدور');
      }
    } catch (error) {
      setError('خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  const togglePermission = (permissionId) => {
    setFormData(prev => ({
      ...prev,
      permission_ids: prev.permission_ids.includes(permissionId)
        ? prev.permission_ids.filter(id => id !== permissionId)
        : [...prev.permission_ids, permissionId]
    }));
  };

  return (
    <div className="modal-overlay">
      <div className="modal large">
        <div className="modal-header">
          <h2>إنشاء دور جديد</h2>
          <Button variant="ghost" onClick={onClose}>×</Button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label>اسم الدور (بالإنجليزية) *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="employee"
              required
            />
          </div>

          <div className="form-group">
            <label>الاسم المعروض *</label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) => setFormData({...formData, display_name: e.target.value})}
              placeholder="موظف"
              required
            />
          </div>

          <div className="form-group">
            <label>الوصف</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              placeholder="وصف الدور وصلاحياته"
              rows="3"
            />
          </div>

          <div className="permissions-section">
            <h3>الصلاحيات</h3>
            <div className="permissions-grid">
              {Object.entries(permissions).map(([category, categoryPermissions]) => (
                <div key={category} className="permission-category">
                  <h4>{category}</h4>
                  <div className="permission-list">
                    {categoryPermissions.map(permission => (
                      <label key={permission.id} className="permission-item">
                        <input
                          type="checkbox"
                          checked={formData.permission_ids.includes(permission.id)}
                          onChange={() => togglePermission(permission.id)}
                        />
                        <span>{permission.display_name}</span>
                        {permission.description && (
                          <small>{permission.description}</small>
                        )}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose}>
              إلغاء
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'جاري الإنشاء...' : 'إنشاء الدور'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// مكون نافذة تحرير الدور
const EditRoleModal = ({ role, permissions, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    display_name: role.display_name || '',
    description: role.description || '',
    permission_ids: role.permissions?.map(p => p.id) || []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`/api/admin/roles/${role.id}`, {
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
        setError(data.error || 'خطأ في تحديث الدور');
      }
    } catch (error) {
      setError('خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  const togglePermission = (permissionId) => {
    setFormData(prev => ({
      ...prev,
      permission_ids: prev.permission_ids.includes(permissionId)
        ? prev.permission_ids.filter(id => id !== permissionId)
        : [...prev.permission_ids, permissionId]
    }));
  };

  return (
    <div className="modal-overlay">
      <div className="modal large">
        <div className="modal-header">
          <h2>تحرير الدور</h2>
          <Button variant="ghost" onClick={onClose}>×</Button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label>اسم الدور</label>
            <input
              type="text"
              value={role.name}
              disabled
              className="disabled"
            />
          </div>

          <div className="form-group">
            <label>الاسم المعروض *</label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) => setFormData({...formData, display_name: e.target.value})}
              required
            />
          </div>

          <div className="form-group">
            <label>الوصف</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              rows="3"
            />
          </div>

          <div className="permissions-section">
            <h3>الصلاحيات</h3>
            <div className="permissions-grid">
              {Object.entries(permissions).map(([category, categoryPermissions]) => (
                <div key={category} className="permission-category">
                  <h4>{category}</h4>
                  <div className="permission-list">
                    {categoryPermissions.map(permission => (
                      <label key={permission.id} className="permission-item">
                        <input
                          type="checkbox"
                          checked={formData.permission_ids.includes(permission.id)}
                          onChange={() => togglePermission(permission.id)}
                        />
                        <span>{permission.display_name}</span>
                        {permission.description && (
                          <small>{permission.description}</small>
                        )}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose}>
              إلغاء
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'جاري التحديث...' : 'تحديث الدور'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RoleManagement;

