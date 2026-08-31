// The data layer over Supabase. Accounts, orders, files and the activity
// timeline live in Postgres behind row level security; auth itself is
// handled by Supabase Auth through AuthContext. Every function here is
// async and returns app-shaped objects (camelCase, files/events attached),
// so views never see database rows.

import {
  CUSTOMER_ACTIONS,
  ORDER_ACTIONS,
  ORDER_STATUSES,
  SHOP_ACTIONS,
} from '@constants/orders.js';
import { supabase } from '@data/supabaseClient.js';

// List views only need file names and counts; the ~megabyte data URLs are
// pulled only when an order detail view asks for them.
const FILE_META_COLUMNS = 'id, file_name, file_type, size, uploaded_by, uploaded_at';
const EVENT_COLUMNS = 'id, actor, kind, label, note, at';
const ORDER_COLUMNS =
  'id, number, user_id, product, qty, size, finish, due_date, notes, status, created_at, updated_at';

const orderSelect = (withFileData) =>
  `${ORDER_COLUMNS}, order_files (${withFileData ? `${FILE_META_COLUMNS}, data_url` : FILE_META_COLUMNS}), order_events (${EVENT_COLUMNS})`;

function fail(error, fallback) {
  throw new Error(
    error?.message || fallback || 'Something went wrong talking to the shop database.',
  );
}

function mapProfile(row) {
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    role: row.role,
    company: row.company,
    phone: row.phone,
    createdAt: row.created_at,
    // Only present (and only visible at all) on admin reads that join it.
    shopNote: row.customer_notes?.note ?? '',
  };
}

function mapFile(row) {
  return {
    id: row.id,
    fileName: row.file_name,
    fileType: row.file_type,
    size: row.size,
    dataUrl: row.data_url,
    uploadedBy: row.uploaded_by,
    uploadedAt: row.uploaded_at,
  };
}

function mapEvent(row) {
  return {
    id: row.id,
    actor: row.actor,
    kind: row.kind,
    label: row.label,
    note: row.note,
    at: row.at,
  };
}

function mapOrder(row) {
  if (!row) return null;
  return {
    id: row.id,
    number: row.number,
    userId: row.user_id,
    product: row.product,
    qty: row.qty,
    size: row.size,
    finish: row.finish,
    dueDate: row.due_date,
    notes: row.notes,
    status: row.status,
    files: (row.order_files || []).map(mapFile),
    events: (row.order_events || []).map(mapEvent),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

async function insertEvent(orderId, { actor, kind, label, note = '' }) {
  const { error } = await supabase
    .from('order_events')
    .insert({ order_id: orderId, actor, kind, label, note });
  if (error) fail(error);
}

async function fetchOrders(withFileData, filter) {
  let query = supabase.from('orders').select(orderSelect(withFileData));
  if (filter) query = filter(query);
  const { data, error } = await query
    .order('updated_at', { ascending: false })
    .order('at', { referencedTable: 'order_events', ascending: true });
  if (error) fail(error);
  return (data || []).map(mapOrder);
}

export const store = {
  // The caller's own profile — what AuthContext hangs onto as `user`.
  async getProfile(id) {
    const { data, error } = await supabase.from('profiles').select('*').eq('id', id).maybeSingle();
    if (error) fail(error);
    return mapProfile(data);
  },

  // Row level security scopes these to the caller: staff see everyone,
  // customers only themselves.
  async getUsers() {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .order('created_at', { ascending: false });
    if (error) fail(error);
    return (data || []).map(mapProfile);
  },

  async getCustomers() {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('role', 'customer')
      .order('created_at', { ascending: false });
    if (error) fail(error);
    return (data || []).map(mapProfile);
  },

  // Admin-side profile read; joins the internal shop note (staff-only table,
  // so the join comes back empty for anyone else).
  async findUserById(id) {
    const { data, error } = await supabase
      .from('profiles')
      .select('*, customer_notes (note)')
      .eq('id', id)
      .maybeSingle();
    if (error) fail(error);
    return mapProfile(data);
  },

  async updateUser(id, { name, company, phone }) {
    const patch = {};
    if (name !== undefined) patch.name = name;
    if (company !== undefined) patch.company = company;
    if (phone !== undefined) patch.phone = phone;
    const { data, error } = await supabase
      .from('profiles')
      .update(patch)
      .eq('id', id)
      .select()
      .maybeSingle();
    if (error) fail(error);
    return mapProfile(data);
  },

  async saveShopNote(userId, note) {
    const { data, error } = await supabase
      .from('customer_notes')
      .update({ note })
      .eq('user_id', userId)
      .select();
    if (error) fail(error);
    if (data?.length) return;
    const { error: insertError } = await supabase
      .from('customer_notes')
      .insert({ user_id: userId, note });
    if (insertError) fail(insertError);
  },

  // Removing a customer deletes their auth account, profile, orders and
  // files in one server-side call, which also refuses staff targets.
  async removeUser(id) {
    const { error } = await supabase.rpc('admin_remove_customer', { target: id });
    if (error) fail(error);
  },

  // Staff get every order; a customer's own policies narrow this to theirs.
  async getOrders() {
    return fetchOrders(false);
  },

  async getOrdersForUser(userId) {
    return fetchOrders(false, (q) => q.eq('user_id', userId));
  },

  async getOrder(id) {
    const { data, error } = await supabase
      .from('orders')
      .select(orderSelect(true))
      .eq('id', id)
      .order('at', { referencedTable: 'order_events', ascending: true })
      .maybeSingle();
    if (error) fail(error);
    return mapOrder(data);
  },

  async createOrder({ userId, product, qty, size, finish, dueDate, notes, files = [] }) {
    const { data, error } = await supabase
      .from('orders')
      .insert({
        user_id: userId,
        product,
        qty: qty || null,
        size: size || '',
        finish: finish || '',
        due_date: dueDate || '',
        notes: notes || '',
        status: files.length > 0 ? 'in-review' : 'awaiting-artwork',
      })
      .select(ORDER_COLUMNS)
      .single();
    if (error) fail(error);

    if (files.length > 0) {
      const { error: filesError } = await supabase.from('order_files').insert(
        files.map((f) => ({
          order_id: data.id,
          file_name: f.fileName,
          file_type: f.fileType,
          size: f.size,
          data_url: f.dataUrl,
          uploaded_by: 'customer',
        })),
      );
      if (filesError) fail(filesError);
    }

    const { error: eventsError } = await supabase.from('order_events').insert([
      { order_id: data.id, actor: 'customer', kind: 'created', label: 'Order placed', note: '' },
      ...files.map((f) => ({
        order_id: data.id,
        actor: 'customer',
        kind: 'file',
        label: `Artwork added: ${f.fileName}`,
        note: '',
      })),
    ]);
    if (eventsError) fail(eventsError);

    return mapOrder({ ...data, order_files: [], order_events: [] });
  },

  // Files carry who put them there: customer files are artwork, shop files
  // are proofs. That difference drives labels, badges, and who may remove what.
  async addArtwork(orderId, file, actor = 'customer') {
    const { data: order, error } = await supabase
      .from('orders')
      .select('id, status')
      .eq('id', orderId)
      .single();
    if (error) fail(error);

    const { error: fileError } = await supabase.from('order_files').insert({
      order_id: orderId,
      file_name: file.fileName,
      file_type: file.fileType,
      size: file.size,
      data_url: file.dataUrl,
      uploaded_by: actor,
    });
    if (fileError) fail(fileError);

    const noun = actor === 'shop' ? 'Proof attached' : 'Artwork added';
    await insertEvent(orderId, { actor, kind: 'file', label: `${noun}: ${file.fileName}` });

    // Fresh customer art lands the order back on the prepress desk.
    if (actor === 'customer' && order.status === 'awaiting-artwork') {
      await this.moveOrder(orderId, 'awaiting-artwork', 'in-review', actor);
    }
  },

  async removeArtwork(orderId, fileId, actor = 'customer') {
    const { data: file, error } = await supabase
      .from('order_files')
      .select('id, file_name, uploaded_by')
      .eq('id', fileId)
      .maybeSingle();
    if (error) fail(error);
    if (!file) return;

    const { error: deleteError } = await supabase.from('order_files').delete().eq('id', fileId);
    if (deleteError) fail(deleteError);

    const noun = file.uploaded_by === 'shop' ? 'Proof removed' : 'Artwork removed';
    await insertEvent(orderId, { actor, kind: 'file', label: `${noun}: ${file.file_name}` });

    // Nothing left to review — hand the order back to the customer.
    const { data: order } = await supabase
      .from('orders')
      .select('status, order_files (id)')
      .eq('id', orderId)
      .maybeSingle();
    if (order?.status === 'in-review' && (order.order_files || []).length === 0) {
      await this.moveOrder(orderId, 'in-review', 'awaiting-artwork', actor);
    }
  },

  // Status changes are compare-and-set on the status the caller saw, so a
  // button rendered from a stale view refuses instead of rewriting history.
  // The database enforces the same rule for customers regardless.
  async moveOrder(orderId, fromStatus, toStatus, actor, { label, note = '' } = {}) {
    const { data, error } = await supabase
      .from('orders')
      .update({ status: toStatus })
      .eq('id', orderId)
      .eq('status', fromStatus)
      .select('id');
    if (error) fail(error);
    if (!data?.length) {
      throw new Error('This order moved on in another tab. Reload to see where it is now.');
    }
    await insertEvent(orderId, {
      actor,
      kind: 'status',
      label: label || `Status: ${ORDER_STATUSES[toStatus].label}`,
      note,
    });
  },

  // All pipeline moves run through the shared action table so the timeline
  // reads the same no matter which panel triggered the change.
  async applyOrderAction(orderId, actionId, note = '') {
    const action = ORDER_ACTIONS[actionId];
    if (!action) throw new Error(`Unknown order action: ${actionId}`);
    if (action.noteRequired && !note.trim()) {
      throw new Error('This action needs a note explaining what should change.');
    }
    const { data: order, error } = await supabase
      .from('orders')
      .select('id, status')
      .eq('id', orderId)
      .single();
    if (error) fail(error);
    const allowed = (action.actor === 'shop' ? SHOP_ACTIONS : CUSTOMER_ACTIONS)[order.status];
    if (!allowed?.includes(actionId)) {
      throw new Error(
        `This order is now ${ORDER_STATUSES[order.status].label}, so “${action.cta}” no longer applies.`,
      );
    }
    await this.moveOrder(orderId, order.status, action.to, action.actor, {
      label: action.label,
      note,
    });
  },

  async addOrderNote(orderId, actor, note) {
    await insertEvent(orderId, {
      actor,
      kind: 'note',
      label: actor === 'shop' ? 'Note from the shop' : 'Note from the customer',
      note,
    });
  },

  async removeOrder(id) {
    const { error } = await supabase.from('orders').delete().eq('id', id);
    if (error) fail(error);
  },
};
