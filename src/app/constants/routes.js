export const ROUTES = {
  home: '/',
  products: '/products',
  work: '/work',
  about: '/about',
  contact: '/contact',
  privacy: '/privacy',
  terms: '/terms',
  login: '/login',
  signup: '/signup',
  forgotPassword: '/forgot-password',
  // Also where Supabase's emailed recovery links land.
  resetPassword: '/reset-password',
  // Bookmarks and outside links still arrive here; it redirects into the portal.
  account: '/account',
  portal: '/portal',
  portalOrders: '/portal/orders',
  portalNewOrder: '/portal/orders/new',
  portalProfile: '/portal/profile',
  admin: '/admin',
  adminOrders: '/admin/orders',
  adminCustomers: '/admin/customers',
};

export const portalOrderPath = (id) => `${ROUTES.portalOrders}/${id}`;
export const adminOrderPath = (id) => `${ROUTES.adminOrders}/${id}`;
export const adminCustomerPath = (id) => `${ROUTES.adminCustomers}/${id}`;

export const NAV_ITEMS = [
  { label: 'Home', to: ROUTES.home },
  { label: 'Products', to: ROUTES.products },
  { label: 'Work', to: ROUTES.work },
  { label: 'About', to: ROUTES.about },
  { label: 'Contact', to: ROUTES.contact },
];
