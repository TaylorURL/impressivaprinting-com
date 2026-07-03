import { Routes, Route } from 'react-router-dom';
import Layout from '@components/Layout.jsx';
import ProtectedRoute from '@components/ProtectedRoute.jsx';
import { ROUTES } from '@constants/routes.js';
import Home from '@views/Home.jsx';
import Products from '@views/Products.jsx';
import Work from '@views/Work.jsx';
import About from '@views/About.jsx';
import Contact from '@views/Contact.jsx';
import Login from '@views/Login.jsx';
import Signup from '@views/Signup.jsx';
import Account from '@views/Account.jsx';
import Admin from '@views/Admin.jsx';
import NotFound from '@views/NotFound.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path={ROUTES.home} element={<Home />} />
        <Route path={ROUTES.products} element={<Products />} />
        <Route path={ROUTES.work} element={<Work />} />
        <Route path={ROUTES.about} element={<About />} />
        <Route path={ROUTES.contact} element={<Contact />} />
        <Route path={ROUTES.login} element={<Login />} />
        <Route path={ROUTES.signup} element={<Signup />} />
        <Route
          path={ROUTES.account}
          element={
            <ProtectedRoute>
              <Account />
            </ProtectedRoute>
          }
        />
        <Route
          path={ROUTES.admin}
          element={
            <ProtectedRoute adminOnly>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
