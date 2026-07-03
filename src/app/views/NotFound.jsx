import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 py-20 text-center sm:px-6">
      <span className="spray text-8xl clip-text street-gradient sm:text-9xl">404</span>
      <h1 className="mt-4 spray text-3xl text-white sm:text-4xl">This Page Got Painted Over</h1>
      <p className="mt-3 max-w-md text-white/60">
        The page you&apos;re after isn&apos;t on the wall. Let&apos;s get you back to something we
        can print.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-4">
        <Button to={ROUTES.home} variant="primary" size="lg">
          Back Home
        </Button>
        <Button to={ROUTES.products} variant="outline" size="lg">
          Browse Products
        </Button>
      </div>
    </div>
  );
}
