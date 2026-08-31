import { Suspense, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import SplitRail from '@taylorurl/split-rail';
import Nav from '@components/Nav.jsx';
import Footer from '@components/Footer.jsx';
import RouteFallback from '@components/RouteFallback.jsx';
import ScrollProgressBar from '@components/ScrollProgressBar.jsx';
import SocialRail from '@components/SocialRail.jsx';

export default function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="relative min-h-dvh overflow-x-clip bg-ink-950">
      {/* What the bar watches to know it has left the top of the page. */}
      <div data-nav-sentinel className="absolute inset-x-0 top-0 h-px" aria-hidden />
      <div
        aria-hidden
        className="grain-layer pointer-events-none fixed inset-0 -z-scrim opacity-[0.04] mix-blend-screen"
      />
      <ScrollProgressBar />
      <SocialRail />
      <Nav />
      {/* The boundary sits inside the chrome, so the bar and the footer stay
          put while a route chunk arrives, and is keyed on the path so each
          route mounts its own. A navigation is a transition, and React holds a
          boundary already on screen at its old content rather than swapping in
          a fallback, so one boundary shared across routes shows the page being
          left for as long as the next chunk takes. */}
      <main className="pt-[var(--header-height)]">
        <Suspense key={pathname} fallback={<RouteFallback />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer>
        <SplitRail />
      </Footer>
    </div>
  );
}
