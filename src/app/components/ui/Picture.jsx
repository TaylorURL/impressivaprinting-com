import { useCallback, useEffect, useRef, useState } from 'react';

// One photo, offered in two formats at each of the widths its layout asks
// for. `src` is the path without an extension; the derivatives sit beside it
// under the same stem, built by scripts/images.sh. The browser takes the
// smallest file its screen and decoder can use and the rendered result is
// the same either way.
//
// `eager` takes the image out of the lazy queue so it starts with the
// document. `priority` is the separate claim that it outranks everything else
// competing for the connection, which only the largest element on the first
// screen can truthfully make; a second image asking for it demotes the first.
// It also decides the decode: asynchronous decoding lets the browser put up a
// frame without the picture and finish it in a later one, which is right for
// everything the reader has not reached and wrong for the one element the
// first screen is measured on.
//
// A photo that loses its request is lost for the rest of the visit. The
// browser asks once, and a connection dropped mid-transfer or an edge that
// answered badly leaves the element in its failed state until the page is
// loaded again - so a single unlucky moment puts a broken frame in the middle
// of the grid and keeps it there. The asks below are that second chance, on a
// growing delay and each under a query no earlier ask used, so nothing answers
// one from the cache that just failed.
//
// The delays grow because the thing that takes a picture away usually takes
// every picture on the screen away with it, and it lasts seconds rather than
// milliseconds: a connection that drops as the page is filling, a hotspot
// changing hands, a tunnel. A single ask half a second later lands inside that
// same gap and fails for the same reason, which reads from here as a picture
// that cannot be fetched and is really a picture nobody waited for. So the
// ladder runs half a second, then two and a half, then seven, which carries an
// element across a ten-second interruption without asking a healthy page for
// anything it would not have asked for anyway.
//
// The second ask also drops the AVIF. A picture element settles on a format
// before it fetches anything and settles on AVIF for every browser that says it
// reads one, so a file that arrives whole and will not decode ends exactly the
// way a file that never arrived does, and the WebP sitting beside it under the
// same stem is never consulted. Asking a decoder a second time for bytes it has
// already refused is not a second ask, it is the same answer - and a reader
// holding its own copy of those bytes from an earlier visit serves them to
// itself without the host being asked at all, which is a correction that
// cannot reach it for as long as the copy lives. So the format that failed
// comes off the table for the rest of the visit and every later ask goes to
// WebP, which every browser that can reach this page can read.
//
// An interruption longer than the ladder is still survivable, because the
// browser will say so: `online` fires when the network comes back and the tab
// says when it is looked at again. Either one buys one more ask. Without them
// a reader who was away for a minute keeps an empty frame however well the
// connection recovered, and the page it is looking at is permanently worse
// than the page it would get by pressing reload.
//
// Each ask is worth exactly one rung, however many times the browser says it
// failed. A failed ask can report itself twice: the round that drops the AVIF
// takes the `source` element away, and an `img` left in the document without
// it chooses again from its own `srcSet` - the WebP under no query at all -
// and fails a second time on the way out. Counted as two, that pair spends two
// rungs for one ask and the later one cancels the ask the earlier one had
// scheduled, so the ladder runs out of rungs an ask early and the frame gives
// up at seven seconds having never asked a third time. So the whole picture
// element is replaced per ask rather than the image inside it, which leaves no
// image in the document without its source, and an ask that has already spent
// its rung is not given another.
//
// What survives all of that is a photo that is not coming, and the frame says
// so rather than going quiet: the layout keeps exactly the space it drew and
// the panel carries the words the picture was there to say. An empty element
// is the one outcome worth avoiding - a wordmark that vanishes and a grid of
// invisible holes read as a page that is broken, where a plain panel with the
// name on it reads as a page with a picture missing from it.
const RETRY_DELAYS_MS = [500, 2500, 7000];
const LAST = RETRY_DELAYS_MS.length;

export default function Picture({
  src,
  alt,
  width,
  height,
  sizes = '100vw',
  className = '',
  eager = false,
  priority = false,
  widths = [400, 800],
}) {
  // `ask` counts every request this element has made and only ever grows, so
  // no later ask can repeat a URL an earlier one failed on. `tries` is how many
  // have failed in the round now running, which is what picks the delay and
  // decides when there is nothing left to try.
  const [ask, setAsk] = useState(0);
  const [tries, setTries] = useState(0);
  const triesRef = useRef(0);
  const askRef = useRef(0);
  const spent = useRef(-1);
  const timer = useRef(null);

  useEffect(() => {
    setAsk(0);
    setTries(0);
    askRef.current = 0;
    spent.current = -1;
  }, [src]);

  useEffect(() => {
    triesRef.current = tries;
  }, [tries]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const onError = useCallback(() => {
    const a = askRef.current;
    if (spent.current === a) return;
    spent.current = a;
    const n = triesRef.current;
    if (n > LAST) return;
    const delay = RETRY_DELAYS_MS[n];
    if (delay === undefined) {
      triesRef.current = n + 1;
      setTries(n + 1);
      return;
    }
    triesRef.current = n + 1;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      // The ref moves with the ask rather than after it, because the browser
      // can report the new ask failed before a passive effect has run.
      askRef.current += 1;
      setTries(n + 1);
      setAsk((a) => a + 1);
    }, delay);
  }, []);

  const exhausted = tries > LAST;

  useEffect(() => {
    if (!exhausted) return undefined;
    // One more ask, and only one: the round restarts at the end of the ladder,
    // so a network that keeps coming and going cannot turn this into a loop.
    const again = () => {
      triesRef.current = LAST;
      askRef.current += 1;
      setTries(LAST);
      setAsk((a) => a + 1);
    };
    const onShown = () => {
      if (document.visibilityState === 'visible') again();
    };
    window.addEventListener('online', again);
    document.addEventListener('visibilitychange', onShown);
    return () => {
      window.removeEventListener('online', again);
      document.removeEventListener('visibilitychange', onShown);
    };
  }, [exhausted]);

  const bust = ask > 0 ? `?retry=${ask}` : '';
  const set = (ext) => widths.map((w) => `${src}-${w}.${ext}${bust} ${w}w`).join(', ');
  const widest = widths[widths.length - 1];

  if (exhausted) {
    return (
      <div
        className={`${className} grid place-items-center overflow-hidden bg-ink-850`}
        style={{ aspectRatio: `${width} / ${height}` }}
        {...(alt ? { role: 'img', 'aria-label': alt } : { 'aria-hidden': true })}
      >
        {alt ? (
          <span className="px-2 text-center font-body text-[0.7rem] leading-tight text-paper-100/70">
            {alt}
          </span>
        ) : null}
      </div>
    );
  }

  return (
    <picture key={ask}>
      {ask === 0 ? <source type="image/avif" srcSet={set('avif')} sizes={sizes} /> : null}
      <img
        src={`${src}-${widest}.webp${bust}`}
        srcSet={set('webp')}
        sizes={sizes}
        alt={alt}
        width={width}
        height={height}
        loading={eager ? 'eager' : 'lazy'}
        fetchPriority={priority ? 'high' : 'auto'}
        {...(priority ? {} : { decoding: 'async' })}
        className={className}
        onError={onError}
      />
    </picture>
  );
}
