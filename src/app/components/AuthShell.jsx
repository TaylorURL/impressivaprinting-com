import { ColorBar } from '@components/PrintMarks.jsx';

export default function AuthShell({ index, kicker, headline, children }) {
  return (
    <section className="mx-auto grid min-h-[calc(100dvh-68px)] max-w-[1400px] grid-cols-1 lg:grid-cols-2">
      <div className="blueprint-ground hidden flex-col justify-between border-r border-paper-100/10 p-10 lg:flex">
        <div className="relative flex items-center justify-between">
          <span className="kicker text-paper-100/50">{index}</span>
          <span className="kicker text-flare">{kicker}</span>
        </div>
        <h2 className="display relative text-7xl leading-[0.82] text-paper-100 xl:text-8xl">
          {headline}
        </h2>
        <ColorBar className="relative h-2" />
      </div>

      <div className="flex items-center justify-center px-5 py-16 sm:px-10">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </section>
  );
}
