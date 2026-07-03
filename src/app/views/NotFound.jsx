import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';

export default function NotFound() {
  return (
    <section className="mx-auto flex min-h-[70vh] max-w-[1400px] flex-col items-center justify-center px-5 py-24 text-center sm:px-8">
      <span className="kicker text-flare">Error — 404</span>
      <h1 className="display mt-6 text-[26vw] leading-[0.8] text-paper-100 sm:text-[12rem]">404</h1>
      <ColorBar className="mt-2 h-2 w-40" />
      <h2 className="display mt-8 text-3xl text-paper-100 sm:text-4xl">Page Not Found</h2>
      <p className="mt-3 max-w-md text-paper-100/55">
        The page you&apos;re looking for doesn&apos;t exist or has moved. Let&apos;s get you back on
        track.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Button to={ROUTES.home} variant="flare" size="lg">
          Back Home
        </Button>
        <Button to={ROUTES.products} variant="outline" size="lg">
          Browse Catalog
        </Button>
      </div>
    </section>
  );
}
