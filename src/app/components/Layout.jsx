import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Nav from '@components/Nav.jsx';
import Footer from '@components/Footer.jsx';

export default function Layout() {
  const { pathname } = useLocation();

  // Reset scroll on route change so each page opens at the top.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  }, [pathname]);

  return (
    <div className="relative min-h-screen overflow-x-clip">
      {/* Street grid backdrop */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-grid-street bg-grid opacity-40 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
      />
      <div aria-hidden className="noise pointer-events-none fixed inset-0 -z-10 opacity-[0.15]" />

      <Nav />
      <main className="pt-28">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
