import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { DecryptedText, SplitText, LetterGlitch } from '@reactbits';

export default function NotFound() {
  return (
    <section className="relative flex min-h-[70vh] flex-col items-center justify-center overflow-hidden px-5 py-24 text-center sm:px-8">
      {/* react-bits LetterGlitch — a glitching wall behind the lost page */}
      <div className="pointer-events-none absolute inset-0 opacity-20">
        <LetterGlitch glitchSpeed={55} fontSize={18} />
      </div>
      <div className="relative mx-auto flex max-w-[1400px] flex-col items-center">
        <span className="kicker text-flare">Error — 404</span>
        <h1 className="display mt-6 text-[26vw] leading-[0.8] text-paper-100 sm:text-[12rem]">
          <DecryptedText text="404" speed={90} encryptedClassName="text-flare/70" />
        </h1>
        <ColorBar className="mt-2 h-2 w-40" />
        <h2 className="display mt-8 text-3xl text-paper-100 sm:text-4xl">
          <SplitText text="Page Not Found" splitType="chars" delay={30} />
        </h2>
        <p className="mt-3 max-w-md text-paper-100/55">
          The page you&apos;re looking for doesn&apos;t exist or has moved. Let&apos;s get you back
          on track.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button to={ROUTES.home} variant="flare" size="lg" magnetic>
            Back Home
          </Button>
          <Button to={ROUTES.products} variant="outline" size="lg" magnetic>
            Browse Catalog
          </Button>
        </div>
      </div>
    </section>
  );
}
