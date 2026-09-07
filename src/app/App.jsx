import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import ClickSpark from '@components/motion/ClickSpark.jsx';
import Layout from '@components/layout/Layout.jsx';
import ProtectedRoute from '@components/routing/ProtectedRoute.jsx';
import RouteFallback from '@components/routing/RouteFallback.jsx';
import RouteHead from '@components/routing/RouteHead.jsx';
import { ROUTES } from '@constants/routes.js';
import { withBuildRefresh } from '@utils/chunk-recovery.js';
import Home from '@views/Home.jsx';

// Home ships with the entry chunk because it is the page most arrivals land
// on; every other route is its own chunk, fetched when someone navigates to
// it. The portal and the admin panel carry the whole tool surface, so keeping
// them out of the storefront download is most of the saving.
const Products = lazy(withBuildRefresh(() => import('@views/Products.jsx')));
const Work = lazy(withBuildRefresh(() => import('@views/Work.jsx')));
const About = lazy(withBuildRefresh(() => import('@views/About.jsx')));
const Contact = lazy(withBuildRefresh(() => import('@views/Contact.jsx')));
const Privacy = lazy(withBuildRefresh(() => import('@views/legal/Privacy.jsx')));
const Terms = lazy(withBuildRefresh(() => import('@views/legal/Terms.jsx')));
const Login = lazy(withBuildRefresh(() => import('@views/auth/Login.jsx')));
const Signup = lazy(withBuildRefresh(() => import('@views/auth/Signup.jsx')));
const ForgotPassword = lazy(withBuildRefresh(() => import('@views/auth/ForgotPassword.jsx')));
const ResetPassword = lazy(withBuildRefresh(() => import('@views/auth/ResetPassword.jsx')));
const NotFound = lazy(withBuildRefresh(() => import('@views/NotFound.jsx')));

const PortalLayout = lazy(withBuildRefresh(() => import('@views/portal/PortalLayout.jsx')));
const PortalDashboard = lazy(withBuildRefresh(() => import('@views/portal/PortalDashboard.jsx')));
const PortalOrders = lazy(withBuildRefresh(() => import('@views/portal/PortalOrders.jsx')));
const NewOrder = lazy(withBuildRefresh(() => import('@views/portal/NewOrder.jsx')));
const PortalOrderDetail = lazy(
  withBuildRefresh(() => import('@views/portal/PortalOrderDetail.jsx')),
);
const PortalProfile = lazy(withBuildRefresh(() => import('@views/portal/PortalProfile.jsx')));

const AdminLayout = lazy(withBuildRefresh(() => import('@views/admin/AdminLayout.jsx')));
const AdminDashboard = lazy(withBuildRefresh(() => import('@views/admin/AdminDashboard.jsx')));
const AdminOrders = lazy(withBuildRefresh(() => import('@views/admin/AdminOrders.jsx')));
const AdminOrderDetail = lazy(withBuildRefresh(() => import('@views/admin/AdminOrderDetail.jsx')));
const AdminCustomers = lazy(withBuildRefresh(() => import('@views/admin/AdminCustomers.jsx')));
const AdminCustomerDetail = lazy(
  withBuildRefresh(() => import('@views/admin/AdminCustomerDetail.jsx')),
);

export default function App() {
  return (
    <>
      <RouteHead />
      <ClickSpark />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path={ROUTES.home} element={<Home />} />
            <Route path={ROUTES.products} element={<Products />} />
            <Route path={ROUTES.work} element={<Work />} />
            <Route path={ROUTES.about} element={<About />} />
            <Route path={ROUTES.contact} element={<Contact />} />
            <Route path={ROUTES.privacy} element={<Privacy />} />
            <Route path={ROUTES.terms} element={<Terms />} />
            <Route path={ROUTES.login} element={<Login />} />
            <Route path={ROUTES.signup} element={<Signup />} />
            <Route path={ROUTES.forgotPassword} element={<ForgotPassword />} />
            <Route path={ROUTES.resetPassword} element={<ResetPassword />} />
            <Route path="*" element={<NotFound />} />
          </Route>

          {/* /account carries no view of its own; it points at the portal. */}
          <Route path={ROUTES.account} element={<Navigate to={ROUTES.portal} replace />} />

          {/* The portal renders its own shell, so it sits beside the storefront
              layout rather than inside it. */}
          <Route
            path={ROUTES.portal}
            element={
              <ProtectedRoute>
                <PortalLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<PortalDashboard />} />
            <Route path="orders" element={<PortalOrders />} />
            <Route path="orders/new" element={<NewOrder />} />
            <Route path="orders/:orderId" element={<PortalOrderDetail />} />
            <Route path="profile" element={<PortalProfile />} />
          </Route>

          <Route
            path={ROUTES.admin}
            element={
              <ProtectedRoute adminOnly>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<AdminDashboard />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="orders/:orderId" element={<AdminOrderDetail />} />
            <Route path="customers" element={<AdminCustomers />} />
            <Route path="customers/:customerId" element={<AdminCustomerDetail />} />
          </Route>
        </Routes>
      </Suspense>
    </>
  );
}
