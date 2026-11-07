import { Component } from 'react';
import { useLocation } from 'react-router-dom';
import Button from '@components/ui/Button.jsx';
import { ColorBar } from '@components/ui/PrintMarks.jsx';
import { ROUTES } from '@constants/routes.js';

/**
 * What the reader gets when a page cannot be loaded.
 *
 * Every route below the home page is a chunk fetched on navigation, and a
 * request that does not land rejects the import. React turns that rejection
 * into a render error, and with nothing above it to catch one it unmounts the
 * entire tree - so the reader was left on an empty document with no nav, no
 * footer and no way back. This is the page that stands there instead: it says
 * the page did not load, offers to try again, and keeps a link to somewhere
 * that works.
 *
 * It is deliberately built from nothing that is loaded on demand. Anything the
 * fallback itself had to fetch could fail for the same reason the page did.
 *
 * The error is not swallowed on the way past: React logs it as it hands it over,
 * so the page reporter still files it.
 */
class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
    this.retry = this.retry.bind(this);
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  // Navigating somewhere else is a new attempt at a different page, so the
  // boundary stands aside for it rather than holding the fallback over a route
  // that was never tried.
  componentDidUpdate(previous) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey) {
      this.setState({ failed: false });
    }
  }

  retry() {
    window.location.reload();
  }

  render() {
    if (!this.state.failed) return this.props.children;

    return (
      <section className="mx-auto flex min-h-[70dvh] max-w-[1400px] flex-col items-center justify-center px-5 py-24 text-center sm:px-8">
        <span className="kicker text-flare">Page Didn&apos;t Load</span>
        <h1 className="display mt-6 max-w-2xl text-4xl leading-[0.95] text-paper-100 sm:text-6xl">
          This Page Didn&apos;t Load
        </h1>
        <ColorBar className="mt-4 h-2 w-40" />
        <p className="mt-6 max-w-md text-paper-100/55">
          Something went wrong fetching this page. Reloading usually sorts it out.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button onClick={this.retry} variant="flare" size="lg">
            Reload The Page
          </Button>
          <Button to={ROUTES.home} variant="outline" size="lg">
            Back Home
          </Button>
        </div>
      </section>
    );
  }
}

/**
 * The boundary, told which route it is standing over so it can stand aside when
 * the reader goes somewhere else.
 */
export default function RouteBoundary({ children }) {
  const location = useLocation();
  return <RouteErrorBoundary resetKey={location.pathname}>{children}</RouteErrorBoundary>;
}
