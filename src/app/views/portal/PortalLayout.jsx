import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { LayoutDashboard, Package, UserRound } from 'lucide-react';
import PanelShell from '@components/panel/PanelShell.jsx';
import RouteFallback from '@components/routing/RouteFallback.jsx';
import { ROUTES } from '@constants/routes.js';

const NAV = [
  { label: 'Dashboard', to: ROUTES.portal, icon: LayoutDashboard, end: true },
  { label: 'Orders', to: ROUTES.portalOrders, icon: Package },
  { label: 'Profile', to: ROUTES.portalProfile, icon: UserRound },
];

export default function PortalLayout() {
  return (
    <PanelShell label="Portal" scope="portal" navItems={NAV} newOrderTo={ROUTES.portalNewOrder}>
      <Suspense fallback={<RouteFallback panel />}>
        <Outlet />
      </Suspense>
    </PanelShell>
  );
}
