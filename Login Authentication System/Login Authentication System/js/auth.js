async function hashString(str) {
  const enc = new TextEncoder();
  const buf = await crypto.subtle.digest('SHA-256', enc.encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}
function getUsers() { try { return JSON.parse(localStorage.getItem('users') || '{}'); } catch { return {}; } }
function saveUsers(users) { localStorage.setItem('users', JSON.stringify(users)); }
async function registerUser({ username, email, password }) {
  const users = getUsers();
  if (users[email]) return { success: false, message: 'User already exists.' };
  for (const k of Object.keys(users)) if (users[k].username.toLowerCase() === username.toLowerCase()) return { success: false, message: 'User already exists.' };
  const passwordHash = await hashString(password);
  users[email] = { username, email, passwordHash };
  saveUsers(users);
  return { success: true };
}
async function loginUser(email, password) {
  const users = getUsers();
  const user = users[email];
  if (!user) return { success: false };
  const passwordHash = await hashString(password);
  if (passwordHash !== user.passwordHash) return { success: false };
  const token = await hashString(email + user.passwordHash);
  localStorage.setItem('authUser', email);
  localStorage.setItem('sessionToken', token);
  return { success: true };
}
function getCurrentUser() { const email = localStorage.getItem('authUser'); if (!email) return null; const users = getUsers(); return users[email] || null; }
async function verifySession() {
  const email = localStorage.getItem('authUser');
  const token = localStorage.getItem('sessionToken');
  if (!email || !token) return false;
  const users = getUsers();
  const user = users[email];
  if (!user) return false;
  const expected = await hashString(email + user.passwordHash);
  return expected === token;
}
function logout() { localStorage.removeItem('authUser'); localStorage.removeItem('sessionToken'); }
