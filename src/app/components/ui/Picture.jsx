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
// of the grid and keeps it there. The retry below is that second ask, on a
// short delay and under a fresh query so nothing answers it from the cache
// that just failed.
//
// The second ask drops the AVIF. A picture element settles on a format before
// it fetches anything and settles on AVIF for every browser that says it reads
// one, so a file that arrives whole and will not decode ends exactly the way a
// file that never arrived does, and the WebP sitting beside it under the same
// stem is never consulted. Asking a decoder a second time for bytes it has
// already refused is not a second ask, it is the same answer - and a reader
// holding its own copy of those bytes from an earlier visit serves them to
// itself without the host being asked at all, which is a correction that
// cannot reach it for as long as the copy lives. So the format that failed
// comes off the table and the second ask goes to WebP, which every browser
// that can reach this page can read. A dropped connection recovers either way,
// and a picture this reader cannot decode now recovers too instead of going.
//
// What survives that is treated as a photo that is not coming: the element
// goes, and the frame the layout drew stays exactly the size it was with the
// caption still on it, so a missing photo reads as a plain panel rather than
// as a page that is broken.
const RETRIES = 1;
const RETRY_DELAY_MS = 500;

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
  const [attempt, setAttempt] = useState(0);
  const timer = useRef(null);

  useEffect(() => {
    setAttempt(0);
  }, [src]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const onError = useCallback(() => {
    setAttempt((n) => {
      if (n > RETRIES) return n;
      if (n === RETRIES) return n + 1;
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setAttempt((c) => c + 1), RETRY_DELAY_MS);
      return n;
    });
  }, []);

  const exhausted = attempt > RETRIES;
  const bust = attempt > 0 ? `?retry=${attempt}` : '';
  const set = (ext) => widths.map((w) => `${src}-${w}.${ext}${bust} ${w}w`).join(', ');
  const widest = widths[widths.length - 1];

  if (exhausted) {
    return (
      <div
        className={className}
        style={{ aspectRatio: `${width} / ${height}` }}
        {...(alt ? { role: 'img', 'aria-label': alt } : { 'aria-hidden': true })}
      />
    );
  }

  return (
    <picture>
      {attempt === 0 ? <source type="image/avif" srcSet={set('avif')} sizes={sizes} /> : null}
      <img
        key={attempt}
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
