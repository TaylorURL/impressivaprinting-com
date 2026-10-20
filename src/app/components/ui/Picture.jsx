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
// growing delay.
//
// EACH ASK IS FOR THE FILE THE MARKUP NAMED. An `img` handed the `src` it
// already holds does nothing, which is why these asks used to carry a query no
// earlier ask had used - but a query is not the way round it. The edge caches
// by the whole URL, so `?retry=1` is a second cache key: it misses the healthy
// copy the edge is already holding, goes to the origin for it, and is
// therefore slower and likelier to fail than the request it is recovering. It
// also puts an address that is not a file on this site into everything that
// watches the site, so one photograph failing reads as faults against several
// different files. What makes the ask instead is the whole picture element
// going and a new one taking its place, which is a fresh `img` with the URLs
// the markup wrote - one request, on the key the edge already has.
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
//
// Dropping it is a decision about the reader rather than about the file, so it
// is taken once and taken for all of them. Held per element, the knowledge that
// this reader gets no AVIF is found and thrown away over and over: the next
// picture offers the format again, loses its own first ask, stands empty for
// the length of a rung, and files its own report - and so does each one the
// reader scrolls into view, for the rest of the visit. The flag the document
// sets at the first failure is what stops that, and it is set in index.html
// because the first screen is in the markup and fails there before the app has
// mounted. An element that reads it off is never offered AVIF at all, so it
// spends no rung, leaves no empty frame, and asks for the one format this
// reader can read on its first ask.
const RETRY_DELAYS_MS = [500, 2500, 7000];
const LAST = RETRY_DELAYS_MS.length;
const LADDER_SECONDS = Math.round(RETRY_DELAYS_MS.reduce((total, ms) => total + ms, 0) / 1000);

// One photograph that never comes is one thing to say, and the same photograph
// can be on the page more than once - the wordmark is in the header and in the
// markup the app replaces. Said per element, a reader who lost one file hears
// about it as many times as the page drew it.
const saidFor = new Set();

const offered = () => typeof window === 'undefined' || window.impressivaAvif !== false;

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
  // `ask` counts every request this element has made and only ever grows. It
  // is what the picture element is keyed on, so each ask replaces the element
  // rather than handing the old one an attribute it already has. `tries` is
  // how many have failed in the round now running, which is what picks the
  // delay and decides when there is nothing left to try.
  const [ask, setAsk] = useState(0);
  const [tries, setTries] = useState(0);
  const [avif, setAvif] = useState(offered);
  const triesRef = useRef(0);
  const askRef = useRef(0);
  const spent = useRef(-1);
  const timer = useRef(null);
  const avifRef = useRef(avif);
  const shown = useRef(false);
  // The file the element actually asked for, taken as it fails. By the time
  // the ladder has run out the img is gone and the panel is in its place, and
  // the widest WebP under the stem is the one nothing chose - naming that is
  // how a report comes to name a file that was never requested.
  const asked = useRef('');

  useEffect(() => {
    setAsk(0);
    setTries(0);
    setAvif(offered());
    askRef.current = 0;
    spent.current = -1;
    shown.current = false;
    asked.current = '';
  }, [src]);

  useEffect(() => {
    avifRef.current = avif;
  }, [avif]);

  // An element that has already drawn its photograph keeps it: there is nothing
  // to recover, and asking again for a file the reader can see would take the
  // picture away to put the same picture back.
  useEffect(() => {
    if (!offered()) {
      setAvif(false);
      return undefined;
    }
    const drop = () => {
      if (!shown.current) setAvif(false);
    };
    window.addEventListener('impressiva:no-avif', drop);
    return () => window.removeEventListener('impressiva:no-avif', drop);
  }, []);

  useEffect(() => {
    triesRef.current = tries;
  }, [tries]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const onLoad = useCallback(() => {
    shown.current = true;
  }, []);

  const onError = useCallback((event) => {
    asked.current = event.currentTarget.currentSrc || event.currentTarget.src || '';
    const a = askRef.current;
    if (spent.current === a) return;
    spent.current = a;
    // Taking the format off the table is itself the next ask, and it happens in
    // this frame rather than after a delay, so it costs no rung. The ladder is
    // for a request that went missing; a format the reader cannot read is not
    // that, and spending a rung on it is what leaves a picture one ask short.
    // The file the browser chose says which of the two it was, because the one
    // written into the markup is the WebP every time.
    if (avifRef.current && /\.avif(\?|$)/.test(event.currentTarget.currentSrc || '')) {
      spent.current = -1;
      setAvif(false);
      return;
    }
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

  const set = (ext) => widths.map((w) => `${src}-${w}.${ext} ${w}w`).join(', ');
  const widest = widths[widths.length - 1];

  const exhausted = tries > LAST;

  // The asks after the first are held by the entry document, because each of
  // them failing while the file is still away is the same fault as the first
  // and filing them turns one photograph into four. What is worth hearing is
  // how it came out, so this says so once when the ladder runs out, naming the
  // file, the asks it took and the time they covered - the thing a report of a
  // single dead request cannot say. `console.error` is where the entry
  // document is listening, so it travels the way every other fault does.
  useEffect(() => {
    if (!exhausted) return;
    if (saidFor.has(src)) return;
    saidFor.add(src);
    const file = asked.current || `${src}-${widest}.webp`;
    console.error(
      `Failed to load img: ${file} - still failing after ${LAST + 1} asks over ${LADDER_SECONDS}s`,
    );
  }, [exhausted, src, widest]);

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
    <picture key={`${ask}-${avif ? 'avif' : 'webp'}`}>
      {ask === 0 && avif ? <source type="image/avif" srcSet={set('avif')} sizes={sizes} /> : null}
      <img
        src={`${src}-${widest}.webp`}
        srcSet={set('webp')}
        {...(ask > 0 ? { 'data-asking': '' } : {})}
        sizes={sizes}
        alt={alt}
        width={width}
        height={height}
        loading={eager ? 'eager' : 'lazy'}
        fetchPriority={priority ? 'high' : 'auto'}
        {...(priority ? {} : { decoding: 'async' })}
        className={className}
        onLoad={onLoad}
        onError={onError}
      />
    </picture>
  );
}
