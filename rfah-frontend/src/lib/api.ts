const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function post(path: string, data: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',   // لو تستعمل جلسات/كوكيز
    body: JSON.stringify(data),
  });
  return res;
}
