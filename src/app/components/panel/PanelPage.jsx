const PANEL_WRAP = 'mx-auto w-full max-w-[1200px] px-5 sm:px-8';

// Compact toolbar header: page title with optional context line above it,
// meta and actions on the right.
export default function PanelPage({ context, title, meta, actions, children }) {
  return (
    <>
      <header className="border-b border-paper-100/8">
        <div className={`${PANEL_WRAP} flex flex-wrap items-center gap-x-4 gap-y-2 py-4`}>
          <div className="min-w-0 flex-1">
            {context ? <p className="text-[11px] text-paper-100/40">{context}</p> : null}
            <h1 className="truncate font-head text-lg font-700 tracking-[-0.01em] text-paper-100">
              {title}
            </h1>
          </div>
          {meta ? (
            <div className="flex shrink-0 items-center text-xs text-paper-100/45">{meta}</div>
          ) : null}
          {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </div>
      </header>
      <div className={`${PANEL_WRAP} animate-panel-in py-6`}>{children}</div>
    </>
  );
}
