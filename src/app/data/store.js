// Front-end-only persistence layer backed by localStorage.
// There is no server: users, sessions and uploads all live in the browser.
// This keeps the demo fully functional while staying build-only.

const KEYS = {
  users: 'impressiva.users',
  session: 'impressiva.session',
  uploads: 'impressiva.uploads',
};

const SEED_ADMIN = {
  id: 'admin-seed',
  name: 'Shop Admin',
  email: 'admin@impressivaprinting.com',
  password: 'admin123',
  role: 'admin',
  createdAt: '2026-01-01T00:00:00.000Z',
};

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

// Generate an id without relying on non-deterministic globals at module load.
function makeId(prefix) {
  const rand = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${Date.now().toString(36)}-${rand}`;
}

function ensureSeed() {
  const users = read(KEYS.users, null);
  if (!users || users.length === 0) {
    write(KEYS.users, [SEED_ADMIN]);
    return [SEED_ADMIN];
  }
  return users;
}

export const store = {
  // --- Users & auth ---
  getUsers() {
    return ensureSeed();
  },

  findUser(email) {
    const target = String(email || '')
      .toLowerCase()
      .trim();
    return this.getUsers().find((u) => u.email.toLowerCase() === target) || null;
  },

  register({ name, email, password }) {
    const users = this.getUsers();
    if (this.findUser(email)) {
      throw new Error('An account with that email already exists.');
    }
    const user = {
      id: makeId('user'),
      name: name.trim(),
      email: email.trim(),
      password,
      role: 'customer',
      createdAt: new Date().toISOString(),
    };
    write(KEYS.users, [...users, user]);
    return user;
  },

  authenticate({ email, password }) {
    const user = this.findUser(email);
    if (!user || user.password !== password) {
      throw new Error('Wrong email or password.');
    }
    return user;
  },

  // --- Session ---
  getSession() {
    const session = read(KEYS.session, null);
    if (!session) return null;
    // Re-resolve against the user table so role/name stay fresh.
    return this.findUser(session.email);
  },

  setSession(user) {
    if (user) write(KEYS.session, { email: user.email });
    else localStorage.removeItem(KEYS.session);
  },

  // --- Uploads ---
  getUploads() {
    return read(KEYS.uploads, []);
  },

  getUploadsForUser(userId) {
    return this.getUploads().filter((u) => u.userId === userId);
  },

  addUpload({ userId, userName, userEmail, fileName, fileType, size, dataUrl, product, notes }) {
    const uploads = this.getUploads();
    const upload = {
      id: makeId('job'),
      userId,
      userName,
      userEmail,
      fileName,
      fileType,
      size,
      dataUrl,
      product: product || 'Unassigned',
      notes: notes || '',
      status: 'new',
      createdAt: new Date().toISOString(),
    };
    write(KEYS.uploads, [upload, ...uploads]);
    return upload;
  },

  removeUpload(id) {
    write(
      KEYS.uploads,
      this.getUploads().filter((u) => u.id !== id),
    );
  },

  setUploadStatus(id, status) {
    write(
      KEYS.uploads,
      this.getUploads().map((u) => (u.id === id ? { ...u, status } : u)),
    );
  },
};

export const UPLOAD_STATUSES = ['new', 'in-production', 'ready', 'archived'];
