// How far down the page the reader is. A scroll timeline drives the fill, so
// the rail costs nothing per frame and nothing re-renders as it moves.
export default function ScrollProgressBar() {
  return (
    <div className="fixed inset-x-0 top-0 z-overlay h-[2px] bg-transparent" aria-hidden>
      <div className="scroll-progress h-full bg-flare" />
    </div>
  );
}
