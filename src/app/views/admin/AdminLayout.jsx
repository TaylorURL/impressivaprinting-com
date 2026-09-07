import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { LayoutDashboard, Package, Users } from 'lucide-react';
import PanelShell from '@components/panel/PanelShell.jsx';
import RouteFallback from '@components/routing/RouteFallback.jsx';
import { ROUTES } from '@constants/routes.js';

const NAV = [
  { label: 'Dashboard', to: ROUTES.admin, icon: LayoutDashboard, end: true },
  { label: 'Orders', to: ROUTES.adminOrders, icon: Package },
  { label: 'Customers', to: ROUTES.adminCustomers, icon: Users },
];

export default function AdminLayout() {
  return (
    <PanelShell label="Admin" scope="admin" navItems={NAV}>
      <Suspense fallback={<RouteFallback panel />}>
        <Outlet />
      </Suspense>
    </PanelShell>
  );
}
