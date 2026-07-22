import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Nav from '@components/Nav.jsx';
import Footer from '@components/Footer.jsx';
import ScrollProgressBar from '@components/ScrollProgressBar.jsx';
import SocialRail from '@components/SocialRail.jsx';

export default function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="relative min-h-screen overflow-x-clip bg-ink-950">
      {/* Fixed paper-grain veil for a printed-surface feel */}
      <div
        aria-hidden
        className="grain pointer-events-none fixed inset-0 -z-10 opacity-[0.04] mix-blend-screen"
      />
      <ScrollProgressBar />
      <SocialRail />
      <Nav />
      <main className="pt-[88px]">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
